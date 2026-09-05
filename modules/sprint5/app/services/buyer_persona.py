from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from app.events.buyer_persona import (
    BuyerPersonaCreated,
    BuyerPersonaDefaultChanged,
    BuyerPersonaDeleted,
    BuyerPersonaUpdated,
)
from app.models.buyer_persona import BuyerPersona, BuyingRole, PersonaStatus, SeniorityLevel
from app.repositories.buyer_persona import BuyerPersonaRepository
from app.repositories.product import ProductRepository
from app.schemas.buyer_persona import BuyerPersonaCreate, BuyerPersonaUpdate
from app.utils.time import utc_now


# ── Domain exceptions ─────────────────────────────────────────────────────────

class BuyerPersonaNotFoundError(EntityNotFoundError):
    error_code = "buyer_persona_not_found"


class BuyerPersonaProductNotFoundError(EntityNotFoundError):
    error_code = "buyer_persona_product_not_found"


class BuyerPersonaBusinessRuleError(BusinessRuleViolationError):
    error_code = "buyer_persona_business_rule_violation"


# ── Service ───────────────────────────────────────────────────────────────────

class BuyerPersonaService:
    def __init__(
        self,
        buyer_persona_repository: BuyerPersonaRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._buyer_persona_repository = buyer_persona_repository
        self._product_repository = product_repository

    async def create(self, payload: BuyerPersonaCreate) -> BuyerPersona:
        await self._ensure_product_exists(payload.product_id)
        await self._ensure_name_unique(payload.name, payload.product_id)

        # Track the previous default before any mutation
        previous_default: BuyerPersona | None = None
        if payload.is_default:
            previous_default = await self._buyer_persona_repository.get_default_for_product(
                payload.product_id
            )

        persona = BuyerPersona(
            product_id=payload.product_id,
            name=payload.name,
            job_title=payload.job_title,
            department=payload.department,
            seniority=payload.seniority,
            buying_role=payload.buying_role,
            influence_level=payload.influence_level,
            decision_power=payload.decision_power,
            responsibilities=payload.responsibilities,
            business_goals=payload.business_goals,
            pain_points=payload.pain_points,
            challenges=payload.challenges,
            objections=payload.objections,
            preferred_channels=payload.preferred_channels,
            preferred_content=payload.preferred_content,
            messaging_themes=payload.messaging_themes,
            keywords=payload.keywords,
            negative_keywords=payload.negative_keywords,
            industry_notes=payload.industry_notes,
            is_default=payload.is_default,
            status=payload.status,
        )

        try:
            # If this new persona becomes default, demote the existing default first
            if payload.is_default and previous_default is not None:
                previous_default.is_default = False
                await self._buyer_persona_repository.update(previous_default)

            created = await self._buyer_persona_repository.create(persona)
            await self._buyer_persona_repository.commit()
        except Exception:
            await self._buyer_persona_repository.rollback()
            raise

        # Emit events after successful commit
        _emit(BuyerPersonaCreated.create(
            persona_id=created.id,
            product_id=created.product_id,
            name=created.name,
            is_default=created.is_default,
        ))
        if payload.is_default:
            _emit(BuyerPersonaDefaultChanged.create(
                product_id=created.product_id,
                new_default_persona_id=created.id,
                previous_default_persona_id=previous_default.id if previous_default else None,
            ))

        return created

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: PersonaStatus | None = None,
        seniority: SeniorityLevel | None = None,
        buying_role: BuyingRole | None = None,
    ) -> tuple[list[BuyerPersona], int]:
        await self._ensure_product_exists(product_id)
        return await self._buyer_persona_repository.list(
            product_id=product_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
            seniority=seniority,
            buying_role=buying_role,
        )

    async def get(self, persona_id: UUID, product_id: UUID | None = None) -> BuyerPersona:
        persona = await self._buyer_persona_repository.get_by_id(persona_id, product_id=product_id)
        if persona is None:
            raise BuyerPersonaNotFoundError("Buyer persona not found")
        return persona

    async def get_default_for_product(self, product_id: UUID) -> BuyerPersona:
        await self._ensure_product_exists(product_id)
        persona = await self._buyer_persona_repository.get_default_for_product(product_id)
        if persona is None:
            raise BuyerPersonaNotFoundError("No default buyer persona found for this product")
        return persona

    async def update(self, persona_id: UUID, payload: BuyerPersonaUpdate) -> BuyerPersona:
        persona = await self.get(persona_id)
        updates = payload.model_dump(exclude_unset=True)

        if "name" in updates and updates["name"] != persona.name:
            await self._ensure_name_unique(updates["name"], persona.product_id)

        previous_default: BuyerPersona | None = None
        is_promoting_to_default = updates.get("is_default") is True and not persona.is_default

        if is_promoting_to_default:
            previous_default = await self._buyer_persona_repository.get_default_for_product(
                persona.product_id
            )

        # Apply all field updates
        _SIMPLE_FIELDS = {
            "name", "job_title", "department",
            "seniority", "buying_role", "influence_level", "decision_power",
            "responsibilities", "business_goals", "pain_points", "challenges", "objections",
            "preferred_channels", "preferred_content", "messaging_themes",
            "keywords", "negative_keywords",
            "industry_notes", "is_default", "status",
        }
        for field in _SIMPLE_FIELDS:
            if field in updates:
                setattr(persona, field, updates[field])

        try:
            if is_promoting_to_default and previous_default is not None and previous_default.id != persona.id:
                previous_default.is_default = False
                await self._buyer_persona_repository.update(previous_default)

            updated = await self._buyer_persona_repository.update(persona)
            await self._buyer_persona_repository.commit()
        except Exception:
            await self._buyer_persona_repository.rollback()
            raise

        _emit(BuyerPersonaUpdated.create(
            persona_id=updated.id,
            product_id=updated.product_id,
            updated_fields=list(updates.keys()),
        ))
        if is_promoting_to_default:
            _emit(BuyerPersonaDefaultChanged.create(
                product_id=updated.product_id,
                new_default_persona_id=updated.id,
                previous_default_persona_id=previous_default.id if previous_default else None,
            ))

        return updated

    async def delete(self, persona_id: UUID) -> None:
        persona = await self.get(persona_id)

        if persona.is_default:
            raise BuyerPersonaBusinessRuleError(
                "Cannot delete the default buyer persona. Assign another persona as default first."
            )

        persona.deleted_at = utc_now()
        persona.status = PersonaStatus.ARCHIVED

        try:
            await self._buyer_persona_repository.soft_delete(persona)
            await self._buyer_persona_repository.commit()
        except Exception:
            await self._buyer_persona_repository.rollback()
            raise

        _emit(BuyerPersonaDeleted.create(persona_id=persona.id, product_id=persona.product_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _ensure_product_exists(self, product_id: UUID) -> None:
        product = await self._product_repository.get_by_id(product_id)
        if product is None:
            raise BuyerPersonaProductNotFoundError("Product not found")

    async def _ensure_name_unique(self, name: str, product_id: UUID) -> None:
        existing = await self._buyer_persona_repository.get_by_name(name, product_id)
        if existing is not None:
            raise BuyerPersonaBusinessRuleError(
                f"A buyer persona named '{name}' already exists for this product"
            )


def _emit(event: object) -> None:
    """
    Fire-and-forget event emission.
    In production wire up an EventBus here (Redis Streams, Kafka, etc.).
    For now events are logged/no-op — the service emits, the bus handles delivery.
    """
    # TODO: inject EventBus and call await event_bus.publish(event)
    pass
