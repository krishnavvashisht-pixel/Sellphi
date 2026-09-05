from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.buyer_persona import BuyerPersona, PersonaStatus, SeniorityLevel
from app.models.product import Product, ProductStatus
from app.schemas.buyer_persona import BuyerPersonaCreate, BuyerPersonaUpdate
from app.services.buyer_persona import (
    BuyerPersonaBusinessRuleError,
    BuyerPersonaNotFoundError,
    BuyerPersonaProductNotFoundError,
    BuyerPersonaService,
)


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeBuyerPersonaRepository:
    def __init__(self, personas: list[BuyerPersona] | None = None) -> None:
        self.personas = personas or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, persona: BuyerPersona) -> BuyerPersona:
        self._hydrate(persona)
        self.personas.append(persona)
        return persona

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: PersonaStatus | None = None,
        seniority: SeniorityLevel | None = None,
        buying_role: object | None = None,
    ) -> tuple[list[BuyerPersona], int]:
        filtered = [
            p for p in self.personas
            if p.product_id == product_id and p.deleted_at is None
        ]
        if status is not None:
            filtered = [p for p in filtered if p.status == status]
        if seniority is not None:
            filtered = [p for p in filtered if p.seniority == seniority]
        if buying_role is not None:
            filtered = [p for p in filtered if p.buying_role == buying_role]
        if search:
            q = search.lower()
            filtered = [
                p for p in filtered
                if q in p.name.lower()
                or (p.job_title is not None and q in p.job_title.lower())
            ]
        return filtered[offset: offset + limit], len(filtered)

    async def get_by_id(self, persona_id: UUID, product_id: UUID | None = None) -> BuyerPersona | None:
        return next(
            (
                p for p in self.personas
                if p.id == persona_id
                and p.deleted_at is None
                and (product_id is None or p.product_id == product_id)
            ),
            None,
        )

    async def get_by_name(self, name: str, product_id: UUID) -> BuyerPersona | None:
        return next(
            (
                p for p in self.personas
                if p.product_id == product_id and p.name == name and p.deleted_at is None
            ),
            None,
        )

    async def get_default_for_product(self, product_id: UUID) -> BuyerPersona | None:
        return next(
            (p for p in self.personas if p.product_id == product_id and p.is_default and p.deleted_at is None),
            None,
        )

    async def get_active_defaults_for_product(self, product_id: UUID) -> list[BuyerPersona]:
        return [p for p in self.personas if p.product_id == product_id and p.is_default and p.deleted_at is None]

    async def update(self, persona: BuyerPersona) -> BuyerPersona:
        persona.updated_at = datetime.now(UTC)
        return persona

    async def soft_delete(self, persona: BuyerPersona) -> BuyerPersona:
        return persona

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, persona: BuyerPersona) -> None:
        now = datetime.now(UTC)
        persona.id = uuid4()
        persona.created_at = now
        persona.updated_at = now
        persona.deleted_at = None
        persona.is_deleted = False


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


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def product_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_product_id() -> UUID:
    return uuid4()


@pytest.fixture
def persona_repo() -> FakeBuyerPersonaRepository:
    return FakeBuyerPersonaRepository()


@pytest.fixture
def service(persona_repo: FakeBuyerPersonaRepository, product_id: UUID) -> BuyerPersonaService:
    product_repo = FakeProductRepository({product_id})
    return BuyerPersonaService(buyer_persona_repository=persona_repo, product_repository=product_repo)


def _create_payload(product_id: UUID, **overrides: object) -> BuyerPersonaCreate:
    return BuyerPersonaCreate(
        product_id=product_id,
        name=overrides.get("name", "VP of Engineering"),  # type: ignore[arg-type]
        job_title=overrides.get("job_title", "VP Engineering"),  # type: ignore[arg-type]
        department=overrides.get("department", "Engineering"),  # type: ignore[arg-type]
        seniority=overrides.get("seniority"),  # type: ignore[arg-type]
        buying_role=overrides.get("buying_role"),  # type: ignore[arg-type]
        influence_level=overrides.get("influence_level"),  # type: ignore[arg-type]
        decision_power=overrides.get("decision_power"),  # type: ignore[arg-type]
        is_default=overrides.get("is_default", False),  # type: ignore[arg-type]
        status=overrides.get("status", PersonaStatus.DRAFT),  # type: ignore[arg-type]
        responsibilities=overrides.get("responsibilities", []),  # type: ignore[arg-type]
        business_goals=overrides.get("business_goals", []),  # type: ignore[arg-type]
        pain_points=overrides.get("pain_points", []),  # type: ignore[arg-type]
        challenges=overrides.get("challenges", []),  # type: ignore[arg-type]
        objections=overrides.get("objections", []),  # type: ignore[arg-type]
        preferred_channels=overrides.get("preferred_channels", []),  # type: ignore[arg-type]
        preferred_content=overrides.get("preferred_content", []),  # type: ignore[arg-type]
        messaging_themes=overrides.get("messaging_themes", []),  # type: ignore[arg-type]
        keywords=overrides.get("keywords", []),  # type: ignore[arg-type]
        negative_keywords=overrides.get("negative_keywords", []),  # type: ignore[arg-type]
        industry_notes=overrides.get("industry_notes", {}),  # type: ignore[arg-type]
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_buyer_persona(
    service: BuyerPersonaService, persona_repo: FakeBuyerPersonaRepository, product_id: UUID
) -> None:
    payload = _create_payload(product_id, name="Enterprise CTO")
    persona = await service.create(payload)

    assert persona.id is not None
    assert persona.name == "Enterprise CTO"
    assert persona.product_id == product_id
    assert persona.is_default is False
    assert persona.status == PersonaStatus.DRAFT
    assert persona_repo.commits == 1


@pytest.mark.asyncio
async def test_get_buyer_persona(service: BuyerPersonaService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    fetched = await service.get(created.id)
    assert fetched.id == created.id
    assert fetched.name == created.name


@pytest.mark.asyncio
async def test_get_buyer_persona_not_found(service: BuyerPersonaService) -> None:
    with pytest.raises(BuyerPersonaNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_create_buyer_persona_product_not_found(service: BuyerPersonaService) -> None:
    payload = _create_payload(uuid4())
    with pytest.raises(BuyerPersonaProductNotFoundError):
        await service.create(payload)


@pytest.mark.asyncio
async def test_list_buyer_personas(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Persona A"))
    await service.create(_create_payload(product_id, name="Persona B"))

    personas, total = await service.list(product_id=product_id)
    assert total == 2
    assert len(personas) == 2


@pytest.mark.asyncio
async def test_update_buyer_persona(service: BuyerPersonaService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    updated = await service.update(created.id, BuyerPersonaUpdate(name="Updated Name"))
    assert updated.name == "Updated Name"


# ── Uniqueness (name, product_id) ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_name_within_product_rejected(
    service: BuyerPersonaService, product_id: UUID
) -> None:
    await service.create(_create_payload(product_id, name="Duplicate Persona"))
    with pytest.raises(BuyerPersonaBusinessRuleError, match="already exists"):
        await service.create(_create_payload(product_id, name="Duplicate Persona"))


@pytest.mark.asyncio
async def test_same_name_allowed_across_products(
    service: BuyerPersonaService, product_id: UUID, other_product_id: UUID
) -> None:
    persona_repo = FakeBuyerPersonaRepository()
    product_repo = FakeProductRepository({product_id, other_product_id})
    isolated_service = BuyerPersonaService(buyer_persona_repository=persona_repo, product_repository=product_repo)

    a = await isolated_service.create(_create_payload(product_id, name="Same Name"))
    b = await isolated_service.create(_create_payload(other_product_id, name="Same Name"))
    assert a.id != b.id


@pytest.mark.asyncio
async def test_rename_to_duplicate_rejected(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Taken Name"))
    other = await service.create(_create_payload(product_id, name="Other Name"))

    with pytest.raises(BuyerPersonaBusinessRuleError, match="already exists"):
        await service.update(other.id, BuyerPersonaUpdate(name="Taken Name"))


# ── Default persona logic ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_default_persona(service: BuyerPersonaService, product_id: UUID) -> None:
    persona = await service.create(_create_payload(product_id, is_default=True))
    assert persona.is_default is True


@pytest.mark.asyncio
async def test_only_one_default_per_product_on_create(
    service: BuyerPersonaService, persona_repo: FakeBuyerPersonaRepository, product_id: UUID
) -> None:
    first = await service.create(_create_payload(product_id, name="First", is_default=True))
    second = await service.create(_create_payload(product_id, name="Second", is_default=True))

    assert second.is_default is True
    first_fetched = await persona_repo.get_by_id(first.id)
    assert first_fetched is not None
    assert first_fetched.is_default is False


@pytest.mark.asyncio
async def test_only_one_default_per_product_on_update(
    service: BuyerPersonaService, persona_repo: FakeBuyerPersonaRepository, product_id: UUID
) -> None:
    first = await service.create(_create_payload(product_id, name="First", is_default=True))
    second = await service.create(_create_payload(product_id, name="Second", is_default=False))

    await service.update(second.id, BuyerPersonaUpdate(is_default=True))

    first_fetched = await persona_repo.get_by_id(first.id)
    assert first_fetched is not None
    assert first_fetched.is_default is False


@pytest.mark.asyncio
async def test_get_default_persona(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, is_default=True))
    default = await service.get_default_for_product(product_id)
    assert default.is_default is True


@pytest.mark.asyncio
async def test_get_default_persona_not_found(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, is_default=False))
    with pytest.raises(BuyerPersonaNotFoundError):
        await service.get_default_for_product(product_id)


@pytest.mark.asyncio
async def test_cannot_delete_default_persona(service: BuyerPersonaService, product_id: UUID) -> None:
    persona = await service.create(_create_payload(product_id, is_default=True))
    with pytest.raises(BuyerPersonaBusinessRuleError, match="Cannot delete the default"):
        await service.delete(persona.id)


# ── Product isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_persona_product_isolation(product_id: UUID, other_product_id: UUID) -> None:
    persona_repo = FakeBuyerPersonaRepository()
    product_repo = FakeProductRepository({product_id, other_product_id})
    service = BuyerPersonaService(buyer_persona_repository=persona_repo, product_repository=product_repo)

    await service.create(_create_payload(product_id, name="Product A Persona"))
    await service.create(_create_payload(other_product_id, name="Product B Persona"))

    personas_a, total_a = await service.list(product_id=product_id)
    personas_b, total_b = await service.list(product_id=other_product_id)

    assert total_a == 1
    assert total_b == 1
    assert personas_a[0].name == "Product A Persona"
    assert personas_b[0].name == "Product B Persona"


# ── decision_power validation (DB-level, 1-10) ───────────────────────────────

@pytest.mark.asyncio
async def test_decision_power_within_range_accepted(service: BuyerPersonaService, product_id: UUID) -> None:
    persona = await service.create(_create_payload(product_id, decision_power=7))
    assert persona.decision_power == 7


def test_decision_power_out_of_range_rejected_by_schema(product_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        BuyerPersonaCreate(product_id=product_id, name="Bad Power", decision_power=11)


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(
    service: BuyerPersonaService, product_id: UUID
) -> None:
    persona = await service.create(_create_payload(product_id))
    assert persona.deleted_at is None

    await service.delete(persona.id)
    assert persona.deleted_at is not None
    assert persona.status == PersonaStatus.ARCHIVED


@pytest.mark.asyncio
async def test_soft_deleted_persona_excluded_from_list(service: BuyerPersonaService, product_id: UUID) -> None:
    keep = await service.create(_create_payload(product_id, name="Keep"))
    delete_me = await service.create(_create_payload(product_id, name="Delete"))
    await service.delete(delete_me.id)

    personas, total = await service.list(product_id=product_id)
    assert total == 1
    assert personas[0].id == keep.id


@pytest.mark.asyncio
async def test_soft_deleted_persona_not_found_by_id(service: BuyerPersonaService, product_id: UUID) -> None:
    persona = await service.create(_create_payload(product_id))
    await service.delete(persona.id)

    with pytest.raises(BuyerPersonaNotFoundError):
        await service.get(persona.id)


# ── Filters ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_filter_by_status(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Active", status=PersonaStatus.ACTIVE))
    await service.create(_create_payload(product_id, name="Draft", status=PersonaStatus.DRAFT))

    active_list, total = await service.list(product_id=product_id, status=PersonaStatus.ACTIVE)
    assert total == 1
    assert active_list[0].name == "Active"


@pytest.mark.asyncio
async def test_list_filter_by_seniority(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="VP", seniority=SeniorityLevel.VP))
    await service.create(_create_payload(product_id, name="Manager", seniority=SeniorityLevel.MANAGER))

    vp_list, total = await service.list(product_id=product_id, seniority=SeniorityLevel.VP)
    assert total == 1
    assert vp_list[0].name == "VP"


@pytest.mark.asyncio
async def test_search_by_name(service: BuyerPersonaService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Enterprise Buyer"))
    await service.create(_create_payload(product_id, name="SMB Prospect"))

    results, total = await service.list(product_id=product_id, search="Enterprise")
    assert total == 1
    assert results[0].name == "Enterprise Buyer"


# ── Pagination ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pagination(service: BuyerPersonaService, product_id: UUID) -> None:
    for i in range(5):
        await service.create(_create_payload(product_id, name=f"Persona {i}"))

    page1, total = await service.list(product_id=product_id, offset=0, limit=2)
    page2, _ = await service.list(product_id=product_id, offset=2, limit=2)
    page3, _ = await service.list(product_id=product_id, offset=4, limit=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
