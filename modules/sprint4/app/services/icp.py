from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from app.events.icp import ICPCreated, ICPDefaultChanged, ICPDeleted, ICPUpdated
from app.models.icp import ICP
from app.repositories.icp import ICPRepository
from app.repositories.product import ProductRepository
from app.schemas.icp import ICPCreate, ICPUpdate
from app.utils.time import utc_now


# ── Domain exceptions ─────────────────────────────────────────────────────────

class ICPNotFoundError(EntityNotFoundError):
    error_code = "icp_not_found"


class ICPProductNotFoundError(EntityNotFoundError):
    error_code = "icp_product_not_found"


class ICPBusinessRuleError(BusinessRuleViolationError):
    error_code = "icp_business_rule_violation"


# ── Service ───────────────────────────────────────────────────────────────────

class ICPService:
    def __init__(
        self,
        icp_repository: ICPRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._icp_repository = icp_repository
        self._product_repository = product_repository

    async def create(self, payload: ICPCreate) -> ICP:
        await self._ensure_product_exists(payload.product_id)
        self._validate_ranges(
            payload.employee_range_min,
            payload.employee_range_max,
            payload.annual_revenue_min,
            payload.annual_revenue_max,
        )

        # Track the previous default before any mutation
        previous_default: ICP | None = None
        if payload.is_default:
            previous_default = await self._icp_repository.get_default_for_product(
                payload.product_id
            )

        icp = ICP(
            product_id=payload.product_id,
            name=payload.name,
            description=payload.description,
            employee_range_min=payload.employee_range_min,
            employee_range_max=payload.employee_range_max,
            annual_revenue_min=payload.annual_revenue_min,
            annual_revenue_max=payload.annual_revenue_max,
            countries=payload.countries,
            states=payload.states,
            cities=payload.cities,
            industries=payload.industries,
            technologies=payload.technologies,
            funding_stages=payload.funding_stages,
            growth_signals=payload.growth_signals,
            keywords=payload.keywords,
            negative_keywords=payload.negative_keywords,
            scoring_rules=payload.scoring_rules,
            is_default=payload.is_default,
            is_active=payload.is_active,
        )

        try:
            # If this new ICP becomes default, demote the existing default first
            if payload.is_default and previous_default is not None:
                previous_default.is_default = False
                await self._icp_repository.update(previous_default)

            created = await self._icp_repository.create(icp)
            await self._icp_repository.commit()
        except Exception:
            await self._icp_repository.rollback()
            raise

        # Emit events after successful commit
        _emit(ICPCreated.create(
            icp_id=created.id,
            product_id=created.product_id,
            name=created.name,
            is_default=created.is_default,
        ))
        if payload.is_default:
            _emit(ICPDefaultChanged.create(
                product_id=created.product_id,
                new_default_icp_id=created.id,
                previous_default_icp_id=previous_default.id if previous_default else None,
            ))

        return created

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ICP], int]:
        await self._ensure_product_exists(product_id)
        return await self._icp_repository.list(
            product_id=product_id,
            offset=offset,
            limit=limit,
            search=search,
            is_active=is_active,
        )

    async def get(self, icp_id: UUID, product_id: UUID | None = None) -> ICP:
        icp = await self._icp_repository.get_by_id(icp_id, product_id=product_id)
        if icp is None:
            raise ICPNotFoundError("ICP not found")
        return icp

    async def get_default_for_product(self, product_id: UUID) -> ICP:
        await self._ensure_product_exists(product_id)
        icp = await self._icp_repository.get_default_for_product(product_id)
        if icp is None:
            raise ICPNotFoundError("No default ICP found for this product")
        return icp

    async def update(self, icp_id: UUID, payload: ICPUpdate) -> ICP:
        icp = await self.get(icp_id)
        updates = payload.model_dump(exclude_unset=True)

        # Validate ranges using final merged values
        self._validate_ranges(
            updates.get("employee_range_min", icp.employee_range_min),
            updates.get("employee_range_max", icp.employee_range_max),
            updates.get("annual_revenue_min", icp.annual_revenue_min),
            updates.get("annual_revenue_max", icp.annual_revenue_max),
        )

        previous_default: ICP | None = None
        is_promoting_to_default = updates.get("is_default") is True and not icp.is_default

        if is_promoting_to_default:
            previous_default = await self._icp_repository.get_default_for_product(icp.product_id)

        # Apply all field updates
        _SIMPLE_FIELDS = {
            "name", "description",
            "employee_range_min", "employee_range_max",
            "annual_revenue_min", "annual_revenue_max",
            "countries", "states", "cities",
            "industries", "technologies", "funding_stages", "growth_signals",
            "keywords", "negative_keywords",
            "scoring_rules", "is_active", "is_default",
        }
        for field in _SIMPLE_FIELDS:
            if field in updates:
                setattr(icp, field, updates[field])

        try:
            if is_promoting_to_default and previous_default is not None and previous_default.id != icp.id:
                previous_default.is_default = False
                await self._icp_repository.update(previous_default)

            updated = await self._icp_repository.update(icp)
            await self._icp_repository.commit()
        except Exception:
            await self._icp_repository.rollback()
            raise

        _emit(ICPUpdated.create(
            icp_id=updated.id,
            product_id=updated.product_id,
            updated_fields=list(updates.keys()),
        ))
        if is_promoting_to_default:
            _emit(ICPDefaultChanged.create(
                product_id=updated.product_id,
                new_default_icp_id=updated.id,
                previous_default_icp_id=previous_default.id if previous_default else None,
            ))

        return updated

    async def delete(self, icp_id: UUID) -> None:
        icp = await self.get(icp_id)

        if icp.is_default:
            raise ICPBusinessRuleError(
                "Cannot delete the default ICP. Assign another ICP as default first."
            )

        icp.deleted_at = utc_now()
        icp.is_active = False

        try:
            await self._icp_repository.soft_delete(icp)
            await self._icp_repository.commit()
        except Exception:
            await self._icp_repository.rollback()
            raise

        _emit(ICPDeleted.create(icp_id=icp.id, product_id=icp.product_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _ensure_product_exists(self, product_id: UUID) -> None:
        product = await self._product_repository.get_by_id(product_id)
        if product is None:
            raise ICPProductNotFoundError("Product not found")

    def _validate_ranges(
        self,
        employee_min: int | None,
        employee_max: int | None,
        revenue_min: int | None,
        revenue_max: int | None,
    ) -> None:
        if employee_min is not None and employee_max is not None:
            if employee_min > employee_max:
                raise ICPBusinessRuleError(
                    "employee_range_min must be less than or equal to employee_range_max"
                )
        if revenue_min is not None and revenue_max is not None:
            if revenue_min > revenue_max:
                raise ICPBusinessRuleError(
                    "annual_revenue_min must be less than or equal to annual_revenue_max"
                )


def _emit(event: object) -> None:
    """
    Fire-and-forget event emission.
    In production wire up an EventBus here (Redis Streams, Kafka, etc.).
    For now events are logged/no-op — the service emits, the bus handles delivery.
    """
    # TODO: inject EventBus and call await event_bus.publish(event)
    pass
