from datetime import date
from typing import Any
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityNotFoundError,
)
from app.events.mission import (
    MissionArchived,
    MissionCompleted,
    MissionCreated,
    MissionDeleted,
    MissionPaused,
    MissionResumed,
    MissionStarted,
    MissionUpdated,
)
from app.models.mission import Mission, MissionStatus
from app.repositories.buyer_persona import BuyerPersonaRepository
from app.repositories.icp import ICPRepository
from app.repositories.mission import MissionRepository
from app.repositories.product import ProductRepository
from app.schemas.mission import MissionCreate, MissionUpdate
from app.utils.time import utc_now


# ── Domain exceptions ─────────────────────────────────────────────────────────

class MissionNotFoundError(EntityNotFoundError):
    error_code = "mission_not_found"


class MissionProductNotFoundError(EntityNotFoundError):
    error_code = "mission_product_not_found"


class MissionICPNotFoundError(EntityNotFoundError):
    error_code = "mission_icp_not_found"


class MissionBusinessRuleError(BusinessRuleViolationError):
    error_code = "mission_business_rule_violation"


class MissionInvalidTransitionError(BusinessRuleViolationError):
    error_code = "mission_invalid_status_transition"


# ── Status transition table ───────────────────────────────────────────────────
# Keyed by action name; value is the set of statuses the mission must currently
# be in for that action to be allowed.

_RUN_ALLOWED_FROM = {MissionStatus.DRAFT}
_PAUSE_ALLOWED_FROM = {MissionStatus.ACTIVE}
_RESUME_ALLOWED_FROM = {MissionStatus.PAUSED}
_COMPLETE_ALLOWED_FROM = {MissionStatus.ACTIVE, MissionStatus.PAUSED}
_ARCHIVE_ALLOWED_FROM = {MissionStatus.DRAFT, MissionStatus.PAUSED, MissionStatus.COMPLETED}


# ── Service ───────────────────────────────────────────────────────────────────

class MissionService:
    def __init__(
        self,
        mission_repository: MissionRepository,
        product_repository: ProductRepository,
        icp_repository: ICPRepository,
        buyer_persona_repository: BuyerPersonaRepository,
    ) -> None:
        self._mission_repository = mission_repository
        self._product_repository = product_repository
        self._icp_repository = icp_repository
        self._buyer_persona_repository = buyer_persona_repository

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, payload: MissionCreate) -> Mission:
        await self._ensure_product_exists(payload.product_id)
        await self._ensure_name_unique(payload.name, payload.product_id)

        if payload.default_icp_id is not None:
            await self._ensure_icp_belongs_to_product(payload.default_icp_id, payload.product_id)

        await self._validate_buyer_personas(payload.product_id, payload.settings)
        self._validate_date_range(payload.start_date, payload.end_date)
        self._validate_limits(
            payload.daily_prospect_limit,
            payload.daily_message_limit,
            payload.max_running_agents,
        )

        mission = Mission(
            product_id=payload.product_id,
            default_icp_id=payload.default_icp_id,
            name=payload.name,
            description=payload.description,
            objective=payload.objective,
            status=MissionStatus.DRAFT,
            priority=payload.priority,
            execution_mode=payload.execution_mode,
            daily_prospect_limit=payload.daily_prospect_limit,
            daily_message_limit=payload.daily_message_limit,
            max_running_agents=payload.max_running_agents,
            start_date=payload.start_date,
            end_date=payload.end_date,
            timezone=payload.timezone,
            schedule=payload.schedule,
            filters=payload.filters,
            settings=payload.settings,
            statistics={},
            created_by=payload.created_by,
        )

        try:
            created = await self._mission_repository.create(mission)
            await self._mission_repository.commit()
        except Exception:
            await self._mission_repository.rollback()
            raise

        _emit(MissionCreated.create(mission_id=created.id, product_id=created.product_id, name=created.name))
        return created

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: MissionStatus | None = None,
    ) -> tuple[list[Mission], int]:
        await self._ensure_product_exists(product_id)
        return await self._mission_repository.list(
            product_id=product_id,
            offset=offset,
            limit=limit,
            search=search,
            status=status,
        )

    async def get(self, mission_id: UUID, product_id: UUID | None = None) -> Mission:
        mission = await self._mission_repository.get_by_id(mission_id, product_id=product_id)
        if mission is None:
            raise MissionNotFoundError("Mission not found")
        return mission

    async def update(self, mission_id: UUID, payload: MissionUpdate) -> Mission:
        mission = await self.get(mission_id)
        if mission.status == MissionStatus.ARCHIVED:
            raise MissionBusinessRuleError("Cannot update an archived mission")

        updates = payload.model_dump(exclude_unset=True)

        if "name" in updates and updates["name"] != mission.name:
            await self._ensure_name_unique(updates["name"], mission.product_id)

        if "default_icp_id" in updates and updates["default_icp_id"] is not None:
            await self._ensure_icp_belongs_to_product(updates["default_icp_id"], mission.product_id)

        if "settings" in updates:
            await self._validate_buyer_personas(mission.product_id, updates["settings"] or {})

        new_start_date = updates.get("start_date", mission.start_date)
        new_end_date = updates.get("end_date", mission.end_date)
        self._validate_date_range(new_start_date, new_end_date)

        self._validate_limits(
            updates.get("daily_prospect_limit", mission.daily_prospect_limit),
            updates.get("daily_message_limit", mission.daily_message_limit),
            updates.get("max_running_agents", mission.max_running_agents),
        )

        # Apply all field updates
        _SIMPLE_FIELDS = {
            "default_icp_id", "name", "description", "objective",
            "priority", "execution_mode",
            "daily_prospect_limit", "daily_message_limit", "max_running_agents",
            "start_date", "end_date", "timezone",
            "schedule", "filters", "settings",
        }
        for field in _SIMPLE_FIELDS:
            if field in updates:
                setattr(mission, field, updates[field])

        try:
            updated = await self._mission_repository.update(mission)
            await self._mission_repository.commit()
        except Exception:
            await self._mission_repository.rollback()
            raise

        _emit(MissionUpdated.create(
            mission_id=updated.id,
            product_id=updated.product_id,
            updated_fields=list(updates.keys()),
        ))
        return updated

    # ── Status transitions ──────────────────────────────────────────────────

    async def run(self, mission_id: UUID) -> Mission:
        """First execution of a mission. DRAFT -> ACTIVE."""
        mission = await self.get(mission_id)
        self._require_status(mission, _RUN_ALLOWED_FROM, "run")

        mission.status = MissionStatus.ACTIVE
        mission.last_run_at = utc_now()
        await self._persist(mission)

        _emit(MissionStarted.create(mission_id=mission.id, product_id=mission.product_id))
        return mission

    async def pause(self, mission_id: UUID) -> Mission:
        """ACTIVE -> PAUSED."""
        mission = await self.get(mission_id)
        self._require_status(mission, _PAUSE_ALLOWED_FROM, "pause")

        mission.status = MissionStatus.PAUSED
        await self._persist(mission)

        _emit(MissionPaused.create(mission_id=mission.id, product_id=mission.product_id))
        return mission

    async def resume(self, mission_id: UUID) -> Mission:
        """Continue a paused mission. PAUSED -> ACTIVE."""
        mission = await self.get(mission_id)
        self._require_status(mission, _RESUME_ALLOWED_FROM, "resume")

        mission.status = MissionStatus.ACTIVE
        await self._persist(mission)

        _emit(MissionResumed.create(mission_id=mission.id, product_id=mission.product_id))
        return mission

    async def complete(self, mission_id: UUID) -> Mission:
        """ACTIVE|PAUSED -> COMPLETED."""
        mission = await self.get(mission_id)
        self._require_status(mission, _COMPLETE_ALLOWED_FROM, "complete")

        mission.status = MissionStatus.COMPLETED
        await self._persist(mission)

        _emit(MissionCompleted.create(mission_id=mission.id, product_id=mission.product_id))
        return mission

    async def archive(self, mission_id: UUID) -> Mission:
        """
        DRAFT|PAUSED|COMPLETED -> ARCHIVED.
        Service-layer capability only; not currently exposed as a REST route
        (the Sprint 6 endpoint list doesn't include one — add
        POST /missions/{id}/archive if/when the product needs it).
        """
        mission = await self.get(mission_id)
        self._require_status(mission, _ARCHIVE_ALLOWED_FROM, "archive")

        mission.status = MissionStatus.ARCHIVED
        await self._persist(mission)

        _emit(MissionArchived.create(mission_id=mission.id, product_id=mission.product_id))
        return mission

    async def delete(self, mission_id: UUID) -> None:
        mission = await self.get(mission_id)

        if mission.status == MissionStatus.ACTIVE:
            raise MissionBusinessRuleError(
                "Cannot delete an active mission. Pause it first."
            )

        mission.deleted_at = utc_now()

        try:
            await self._mission_repository.soft_delete(mission)
            await self._mission_repository.commit()
        except Exception:
            await self._mission_repository.rollback()
            raise

        _emit(MissionDeleted.create(mission_id=mission.id, product_id=mission.product_id))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _require_status(
        self, mission: Mission, allowed_from: set[MissionStatus], action: str
    ) -> None:
        if mission.status not in allowed_from:
            raise MissionInvalidTransitionError(
                f"Cannot {action} a mission with status '{mission.status.value}'"
            )

    async def _persist(self, mission: Mission) -> Mission:
        try:
            updated = await self._mission_repository.update(mission)
            await self._mission_repository.commit()
            return updated
        except Exception:
            await self._mission_repository.rollback()
            raise

    async def _ensure_product_exists(self, product_id: UUID) -> None:
        product = await self._product_repository.get_by_id(product_id)
        if product is None:
            raise MissionProductNotFoundError("Product not found")

    async def _ensure_icp_belongs_to_product(self, icp_id: UUID, product_id: UUID) -> None:
        icp = await self._icp_repository.get_by_id(icp_id, product_id=product_id)
        if icp is None:
            raise MissionICPNotFoundError(
                "Default ICP not found for this product"
            )

    async def _ensure_name_unique(self, name: str, product_id: UUID) -> None:
        existing = await self._mission_repository.get_by_name(name, product_id)
        if existing is not None:
            raise MissionBusinessRuleError(
                f"A mission named '{name}' already exists for this product"
            )

    async def _validate_buyer_personas(self, product_id: UUID, settings: dict[str, Any]) -> None:
        """
        Forward-compatibility hook: if the caller passes settings["buyer_persona_ids"],
        confirm each one belongs to the mission's product. Missions don't have a
        dedicated buyer-persona column yet — that lands with the AI workflow sprint —
        so this only validates, it doesn't yet drive any behavior.
        """
        buyer_persona_ids = (settings or {}).get("buyer_persona_ids") or []
        for raw_id in buyer_persona_ids:
            persona_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
            persona = await self._buyer_persona_repository.get_by_id(persona_id, product_id=product_id)
            if persona is None:
                raise MissionBusinessRuleError(
                    f"Buyer persona {persona_id} does not belong to this product"
                )

    def _validate_date_range(self, start_date: date | None, end_date: date | None) -> None:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise MissionBusinessRuleError("start_date must be before or equal to end_date")

    def _validate_limits(
        self, daily_prospect_limit: int, daily_message_limit: int, max_running_agents: int
    ) -> None:
        if daily_prospect_limit <= 0:
            raise MissionBusinessRuleError("daily_prospect_limit must be a positive integer")
        if daily_message_limit <= 0:
            raise MissionBusinessRuleError("daily_message_limit must be a positive integer")
        if max_running_agents <= 0:
            raise MissionBusinessRuleError("max_running_agents must be a positive integer")


def _emit(event: object) -> None:
    """
    Fire-and-forget event emission.
    In production wire up an EventBus here (Redis Streams, Kafka, etc.).
    For now events are logged/no-op — the service emits, the bus handles delivery.
    """
    # TODO: inject EventBus and call await event_bus.publish(event)
    pass
