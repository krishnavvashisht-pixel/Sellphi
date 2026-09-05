from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.models.buyer_persona import BuyerPersona, PersonaStatus
from app.models.icp import ICP
from app.models.mission import Mission, MissionExecutionMode, MissionPriority, MissionStatus
from app.models.product import Product, ProductStatus
from app.schemas.mission import MissionCreate, MissionUpdate
from app.services.mission import (
    MissionBusinessRuleError,
    MissionICPNotFoundError,
    MissionInvalidTransitionError,
    MissionNotFoundError,
    MissionProductNotFoundError,
    MissionService,
)


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeMissionRepository:
    def __init__(self, missions: list[Mission] | None = None) -> None:
        self.missions = missions or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, mission: Mission) -> Mission:
        self._hydrate(mission)
        self.missions.append(mission)
        return mission

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: MissionStatus | None = None,
    ) -> tuple[list[Mission], int]:
        filtered = [
            m for m in self.missions
            if m.product_id == product_id and m.deleted_at is None
        ]
        if status is not None:
            filtered = [m for m in filtered if m.status == status]
        if search:
            q = search.lower()
            filtered = [
                m for m in filtered
                if q in m.name.lower()
                or (m.description is not None and q in m.description.lower())
                or (m.objective is not None and q in m.objective.lower())
            ]
        return filtered[offset: offset + limit], len(filtered)

    async def get_by_id(self, mission_id: UUID, product_id: UUID | None = None) -> Mission | None:
        return next(
            (
                m for m in self.missions
                if m.id == mission_id
                and m.deleted_at is None
                and (product_id is None or m.product_id == product_id)
            ),
            None,
        )

    async def get_by_name(self, name: str, product_id: UUID) -> Mission | None:
        return next(
            (
                m for m in self.missions
                if m.product_id == product_id and m.name == name and m.deleted_at is None
            ),
            None,
        )

    async def update(self, mission: Mission) -> Mission:
        mission.updated_at = datetime.now(UTC)
        return mission

    async def soft_delete(self, mission: Mission) -> Mission:
        return mission

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, mission: Mission) -> None:
        now = datetime.now(UTC)
        mission.id = uuid4()
        mission.created_at = now
        mission.updated_at = now
        mission.deleted_at = None
        mission.is_deleted = False


class FakeProductRepository:
    def __init__(self, product_ids: set[UUID]) -> None:
        self.product_ids = product_ids

    async def get_by_id(self, product_id: UUID, workspace_id: UUID | None = None) -> Product | None:
        if product_id not in self.product_ids:
            return None
        now = datetime.now(UTC)
        product = Product(
            workspace_id=uuid4(),
            name="Test Product",
            slug="test-product",
            status=ProductStatus.ACTIVE,
            settings={},
        )
        product.id = product_id
        product.created_at = now
        product.updated_at = now
        product.deleted_at = None
        product.is_deleted = False
        return product


class FakeICPRepository:
    def __init__(self) -> None:
        self.icps: dict[UUID, UUID] = {}  # icp_id -> product_id

    def register(self, icp_id: UUID, product_id: UUID) -> None:
        self.icps[icp_id] = product_id

    async def get_by_id(self, icp_id: UUID, product_id: UUID | None = None) -> ICP | None:
        owning_product_id = self.icps.get(icp_id)
        if owning_product_id is None:
            return None
        if product_id is not None and owning_product_id != product_id:
            return None
        now = datetime.now(UTC)
        icp = ICP(product_id=owning_product_id, name="Test ICP")
        icp.id = icp_id
        icp.created_at = now
        icp.updated_at = now
        icp.deleted_at = None
        icp.is_deleted = False
        return icp


class FakeBuyerPersonaRepository:
    def __init__(self) -> None:
        self.personas: dict[UUID, UUID] = {}  # persona_id -> product_id

    def register(self, persona_id: UUID, product_id: UUID) -> None:
        self.personas[persona_id] = product_id

    async def get_by_id(self, persona_id: UUID, product_id: UUID | None = None) -> BuyerPersona | None:
        owning_product_id = self.personas.get(persona_id)
        if owning_product_id is None:
            return None
        if product_id is not None and owning_product_id != product_id:
            return None
        now = datetime.now(UTC)
        persona = BuyerPersona(product_id=owning_product_id, name="Test Persona", status=PersonaStatus.ACTIVE)
        persona.id = persona_id
        persona.created_at = now
        persona.updated_at = now
        persona.deleted_at = None
        persona.is_deleted = False
        return persona


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def product_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_product_id() -> UUID:
    return uuid4()


@pytest.fixture
def mission_repo() -> FakeMissionRepository:
    return FakeMissionRepository()


@pytest.fixture
def icp_repo() -> FakeICPRepository:
    return FakeICPRepository()


@pytest.fixture
def buyer_persona_repo() -> FakeBuyerPersonaRepository:
    return FakeBuyerPersonaRepository()


@pytest.fixture
def service(
    mission_repo: FakeMissionRepository,
    icp_repo: FakeICPRepository,
    buyer_persona_repo: FakeBuyerPersonaRepository,
    product_id: UUID,
    other_product_id: UUID,
) -> MissionService:
    product_repo = FakeProductRepository({product_id, other_product_id})
    return MissionService(
        mission_repository=mission_repo,
        product_repository=product_repo,
        icp_repository=icp_repo,
        buyer_persona_repository=buyer_persona_repo,
    )


def _create_payload(product_id: UUID, **overrides: object) -> MissionCreate:
    return MissionCreate(
        product_id=product_id,
        default_icp_id=overrides.get("default_icp_id"),  # type: ignore[arg-type]
        name=overrides.get("name", "Q3 Outbound Push"),  # type: ignore[arg-type]
        description=overrides.get("description"),  # type: ignore[arg-type]
        objective=overrides.get("objective"),  # type: ignore[arg-type]
        priority=overrides.get("priority", MissionPriority.MEDIUM),  # type: ignore[arg-type]
        execution_mode=overrides.get("execution_mode", MissionExecutionMode.ASSISTED),  # type: ignore[arg-type]
        daily_prospect_limit=overrides.get("daily_prospect_limit", 50),  # type: ignore[arg-type]
        daily_message_limit=overrides.get("daily_message_limit", 50),  # type: ignore[arg-type]
        max_running_agents=overrides.get("max_running_agents", 1),  # type: ignore[arg-type]
        start_date=overrides.get("start_date"),  # type: ignore[arg-type]
        end_date=overrides.get("end_date"),  # type: ignore[arg-type]
        timezone=overrides.get("timezone", "UTC"),  # type: ignore[arg-type]
        schedule=overrides.get("schedule", {}),  # type: ignore[arg-type]
        filters=overrides.get("filters", {}),  # type: ignore[arg-type]
        settings=overrides.get("settings", {}),  # type: ignore[arg-type]
        created_by=overrides.get("created_by"),  # type: ignore[arg-type]
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_mission(
    service: MissionService, mission_repo: FakeMissionRepository, product_id: UUID
) -> None:
    mission = await service.create(_create_payload(product_id, name="Enterprise Outbound"))

    assert mission.id is not None
    assert mission.name == "Enterprise Outbound"
    assert mission.product_id == product_id
    assert mission.status == MissionStatus.DRAFT
    assert mission_repo.commits == 1


@pytest.mark.asyncio
async def test_create_mission_product_not_found(service: MissionService) -> None:
    with pytest.raises(MissionProductNotFoundError):
        await service.create(_create_payload(uuid4()))


@pytest.mark.asyncio
async def test_get_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    fetched = await service.get(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_mission_not_found(service: MissionService) -> None:
    with pytest.raises(MissionNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_update_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    updated = await service.update(created.id, MissionUpdate(name="Renamed Mission"))
    assert updated.name == "Renamed Mission"


@pytest.mark.asyncio
async def test_cannot_update_archived_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.archive(created.id)

    with pytest.raises(MissionBusinessRuleError, match="archived"):
        await service.update(created.id, MissionUpdate(name="New Name"))


# ── Name uniqueness ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_name_within_product_rejected(service: MissionService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Duplicate Mission"))
    with pytest.raises(MissionBusinessRuleError, match="already exists"):
        await service.create(_create_payload(product_id, name="Duplicate Mission"))


@pytest.mark.asyncio
async def test_same_name_allowed_across_products(
    service: MissionService, product_id: UUID, other_product_id: UUID
) -> None:
    a = await service.create(_create_payload(product_id, name="Same Name"))
    b = await service.create(_create_payload(other_product_id, name="Same Name"))
    assert a.id != b.id


@pytest.mark.asyncio
async def test_rename_to_duplicate_rejected(service: MissionService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Taken"))
    other = await service.create(_create_payload(product_id, name="Other"))

    with pytest.raises(MissionBusinessRuleError, match="already exists"):
        await service.update(other.id, MissionUpdate(name="Taken"))


# ── ICP validation ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_default_icp_must_belong_to_same_product(
    service: MissionService, icp_repo: FakeICPRepository, product_id: UUID, other_product_id: UUID
) -> None:
    foreign_icp_id = uuid4()
    icp_repo.register(foreign_icp_id, other_product_id)

    with pytest.raises(MissionICPNotFoundError):
        await service.create(_create_payload(product_id, default_icp_id=foreign_icp_id))


@pytest.mark.asyncio
async def test_default_icp_belonging_to_product_accepted(
    service: MissionService, icp_repo: FakeICPRepository, product_id: UUID
) -> None:
    icp_id = uuid4()
    icp_repo.register(icp_id, product_id)

    mission = await service.create(_create_payload(product_id, default_icp_id=icp_id))
    assert mission.default_icp_id == icp_id


@pytest.mark.asyncio
async def test_update_default_icp_validated_against_product(
    service: MissionService, icp_repo: FakeICPRepository, product_id: UUID, other_product_id: UUID
) -> None:
    created = await service.create(_create_payload(product_id))
    foreign_icp_id = uuid4()
    icp_repo.register(foreign_icp_id, other_product_id)

    with pytest.raises(MissionICPNotFoundError):
        await service.update(created.id, MissionUpdate(default_icp_id=foreign_icp_id))


# ── Buyer persona validation (future compatibility) ──────────────────────────

@pytest.mark.asyncio
async def test_buyer_persona_ids_must_belong_to_product(
    service: MissionService, buyer_persona_repo: FakeBuyerPersonaRepository, product_id: UUID, other_product_id: UUID
) -> None:
    foreign_persona_id = uuid4()
    buyer_persona_repo.register(foreign_persona_id, other_product_id)

    with pytest.raises(MissionBusinessRuleError, match="does not belong to this product"):
        await service.create(
            _create_payload(product_id, settings={"buyer_persona_ids": [str(foreign_persona_id)]})
        )


@pytest.mark.asyncio
async def test_buyer_persona_ids_belonging_to_product_accepted(
    service: MissionService, buyer_persona_repo: FakeBuyerPersonaRepository, product_id: UUID
) -> None:
    persona_id = uuid4()
    buyer_persona_repo.register(persona_id, product_id)

    mission = await service.create(
        _create_payload(product_id, settings={"buyer_persona_ids": [str(persona_id)]})
    )
    assert mission.settings["buyer_persona_ids"] == [str(persona_id)]


# ── Date range validation ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_date_range_accepted(service: MissionService, product_id: UUID) -> None:
    mission = await service.create(
        _create_payload(
            product_id,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 9, 1),
        )
    )
    assert mission.start_date == date(2026, 8, 1)
    assert mission.end_date == date(2026, 9, 1)


def test_end_date_before_start_date_rejected_by_schema(product_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        MissionCreate(
            product_id=product_id,
            name="Bad Dates",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 8, 1),
        )


@pytest.mark.asyncio
async def test_update_partial_date_validated_against_persisted_value(
    service: MissionService, product_id: UUID
) -> None:
    created = await service.create(
        _create_payload(product_id, start_date=date(2026, 8, 1), end_date=date(2026, 9, 1))
    )

    with pytest.raises(MissionBusinessRuleError, match="start_date"):
        await service.update(created.id, MissionUpdate(start_date=date(2026, 10, 1)))


# ── Limit validation ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_positive_limits_accepted(service: MissionService, product_id: UUID) -> None:
    mission = await service.create(
        _create_payload(product_id, daily_prospect_limit=10, daily_message_limit=20, max_running_agents=2)
    )
    assert mission.daily_prospect_limit == 10


def test_zero_daily_prospect_limit_rejected_by_schema(product_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        MissionCreate(product_id=product_id, name="Bad Limit", daily_prospect_limit=0)


def test_negative_max_running_agents_rejected_by_schema(product_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        MissionCreate(product_id=product_id, name="Bad Agents", max_running_agents=-1)


# ── Status transitions ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_transitions_draft_to_active(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    assert created.status == MissionStatus.DRAFT

    started = await service.run(created.id)
    assert started.status == MissionStatus.ACTIVE
    assert started.last_run_at is not None


@pytest.mark.asyncio
async def test_run_twice_rejected(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)

    with pytest.raises(MissionInvalidTransitionError):
        await service.run(created.id)


@pytest.mark.asyncio
async def test_pause_active_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)

    paused = await service.pause(created.id)
    assert paused.status == MissionStatus.PAUSED


@pytest.mark.asyncio
async def test_cannot_pause_draft_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    with pytest.raises(MissionInvalidTransitionError):
        await service.pause(created.id)


@pytest.mark.asyncio
async def test_resume_paused_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)
    await service.pause(created.id)

    resumed = await service.resume(created.id)
    assert resumed.status == MissionStatus.ACTIVE


@pytest.mark.asyncio
async def test_cannot_resume_draft_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    with pytest.raises(MissionInvalidTransitionError):
        await service.resume(created.id)


@pytest.mark.asyncio
async def test_complete_active_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)

    completed = await service.complete(created.id)
    assert completed.status == MissionStatus.COMPLETED


@pytest.mark.asyncio
async def test_complete_paused_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)
    await service.pause(created.id)

    completed = await service.complete(created.id)
    assert completed.status == MissionStatus.COMPLETED


@pytest.mark.asyncio
async def test_cannot_complete_draft_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    with pytest.raises(MissionInvalidTransitionError):
        await service.complete(created.id)


@pytest.mark.asyncio
async def test_archive_completed_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)
    await service.complete(created.id)

    archived = await service.archive(created.id)
    assert archived.status == MissionStatus.ARCHIVED


@pytest.mark.asyncio
async def test_cannot_archive_active_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)

    with pytest.raises(MissionInvalidTransitionError):
        await service.archive(created.id)


@pytest.mark.asyncio
async def test_cannot_transition_archived_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.archive(created.id)

    with pytest.raises(MissionInvalidTransitionError):
        await service.run(created.id)


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    assert created.deleted_at is None

    await service.delete(created.id)
    assert created.deleted_at is not None


@pytest.mark.asyncio
async def test_cannot_delete_active_mission(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.run(created.id)

    with pytest.raises(MissionBusinessRuleError, match="active mission"):
        await service.delete(created.id)


@pytest.mark.asyncio
async def test_delete_draft_mission_allowed(service: MissionService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.delete(created.id)  # DRAFT missions may be deleted directly

    with pytest.raises(MissionNotFoundError):
        await service.get(created.id)


@pytest.mark.asyncio
async def test_soft_deleted_mission_excluded_from_list(service: MissionService, product_id: UUID) -> None:
    keep = await service.create(_create_payload(product_id, name="Keep"))
    delete_me = await service.create(_create_payload(product_id, name="Delete"))
    await service.delete(delete_me.id)

    missions, total = await service.list(product_id=product_id)
    assert total == 1
    assert missions[0].id == keep.id


# ── Product isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mission_product_isolation(service: MissionService, product_id: UUID, other_product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Product A Mission"))
    await service.create(_create_payload(other_product_id, name="Product B Mission"))

    missions_a, total_a = await service.list(product_id=product_id)
    missions_b, total_b = await service.list(product_id=other_product_id)

    assert total_a == 1
    assert total_b == 1
    assert missions_a[0].name == "Product A Mission"
    assert missions_b[0].name == "Product B Mission"


# ── Filters ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_filter_by_status(service: MissionService, product_id: UUID) -> None:
    draft = await service.create(_create_payload(product_id, name="Draft Mission"))
    active_mission = await service.create(_create_payload(product_id, name="Active Mission"))
    await service.run(active_mission.id)

    active_list, total = await service.list(product_id=product_id, status=MissionStatus.ACTIVE)
    assert total == 1
    assert active_list[0].id == active_mission.id


@pytest.mark.asyncio
async def test_search_by_name(service: MissionService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Enterprise Outbound"))
    await service.create(_create_payload(product_id, name="SMB Outbound"))

    results, total = await service.list(product_id=product_id, search="Enterprise")
    assert total == 1
    assert results[0].name == "Enterprise Outbound"


# ── Pagination ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pagination(service: MissionService, product_id: UUID) -> None:
    for i in range(5):
        await service.create(_create_payload(product_id, name=f"Mission {i}"))

    page1, total = await service.list(product_id=product_id, offset=0, limit=2)
    page2, _ = await service.list(product_id=product_id, offset=2, limit=2)
    page3, _ = await service.list(product_id=product_id, offset=4, limit=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
