from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.company import Company, CompanyStatus, FundingStage
from app.models.mission import Mission, MissionStatus
from app.models.product import Product, ProductStatus
from app.models.workspace import Workspace
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company import (
    CompanyBusinessRuleError,
    CompanyDuplicateDomainError,
    CompanyInvalidTransitionError,
    CompanyMissionNotFoundError,
    CompanyNotFoundError,
    CompanyWorkspaceNotFoundError,
    CompanyService,
)


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeCompanyRepository:
    def __init__(self, companies: list[Company] | None = None) -> None:
        self.companies = companies or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, company: Company) -> Company:
        self._hydrate(company)
        self.companies.append(company)
        return company

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        industry: str | None = None,
        status: CompanyStatus | None = None,
        funding_stage: FundingStage | None = None,
        company_size: str | None = None,
        country: str | None = None,
        mission_id: UUID | None = None,
    ) -> tuple[list[Company], int]:
        filtered = [
            c for c in self.companies
            if c.workspace_id == workspace_id and c.deleted_at is None
        ]
        if status is not None:
            filtered = [c for c in filtered if c.status == status]
        if industry is not None:
            filtered = [c for c in filtered if c.industry == industry]
        if funding_stage is not None:
            filtered = [c for c in filtered if c.funding_stage == funding_stage]
        if company_size is not None:
            filtered = [c for c in filtered if c.company_size == company_size]
        if country is not None:
            filtered = [c for c in filtered if c.headquarters_country == country]
        if mission_id is not None:
            filtered = [c for c in filtered if c.mission_id == mission_id]
        if search:
            q = search.lower()
            filtered = [
                c for c in filtered
                if q in c.name.lower()
                or (c.domain is not None and q in c.domain.lower())
                or (c.website is not None and q in c.website.lower())
                or (c.industry is not None and q in c.industry.lower())
            ]
        return filtered[offset: offset + limit], len(filtered)

    async def get_by_id(self, company_id: UUID, workspace_id: UUID | None = None) -> Company | None:
        return next(
            (
                c for c in self.companies
                if c.id == company_id
                and c.deleted_at is None
                and (workspace_id is None or c.workspace_id == workspace_id)
            ),
            None,
        )

    async def get_by_domain(self, domain: str, workspace_id: UUID) -> Company | None:
        return next(
            (
                c for c in self.companies
                if c.workspace_id == workspace_id and c.domain == domain and c.deleted_at is None
            ),
            None,
        )

    async def update(self, company: Company) -> Company:
        company.updated_at = datetime.now(UTC)
        return company

    async def soft_delete(self, company: Company) -> Company:
        return company

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, company: Company) -> None:
        now = datetime.now(UTC)
        company.id = uuid4()
        company.created_at = now
        company.updated_at = now
        company.deleted_at = None
        company.is_deleted = False


class FakeWorkspaceRepository:
    def __init__(self, workspace_ids: set[UUID]) -> None:
        self.workspace_ids = workspace_ids

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        if workspace_id not in self.workspace_ids:
            return None
        now = datetime.now(UTC)
        workspace = Workspace(name="Test Workspace", slug="test-workspace")
        workspace.id = workspace_id
        workspace.created_at = now
        workspace.updated_at = now
        workspace.deleted_at = None
        workspace.is_deleted = False
        return workspace


class FakeMissionRepository:
    def __init__(self) -> None:
        self.missions: dict[UUID, UUID] = {}  # mission_id -> product_id

    def register(self, mission_id: UUID, product_id: UUID) -> None:
        self.missions[mission_id] = product_id

    async def get_by_id(self, mission_id: UUID, product_id: UUID | None = None) -> Mission | None:
        owning_product_id = self.missions.get(mission_id)
        if owning_product_id is None:
            return None
        if product_id is not None and owning_product_id != product_id:
            return None
        now = datetime.now(UTC)
        mission = Mission(product_id=owning_product_id, name="Test Mission", status=MissionStatus.DRAFT)
        mission.id = mission_id
        mission.created_at = now
        mission.updated_at = now
        mission.deleted_at = None
        mission.is_deleted = False
        return mission


class FakeProductRepository:
    def __init__(self) -> None:
        self.products: dict[UUID, UUID] = {}  # product_id -> workspace_id

    def register(self, product_id: UUID, workspace_id: UUID) -> None:
        self.products[product_id] = workspace_id

    async def get_by_id(self, product_id: UUID, workspace_id: UUID | None = None) -> Product | None:
        owning_workspace_id = self.products.get(product_id)
        if owning_workspace_id is None:
            return None
        now = datetime.now(UTC)
        product = Product(
            workspace_id=owning_workspace_id,
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
def workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_workspace_id() -> UUID:
    return uuid4()


@pytest.fixture
def company_repo() -> FakeCompanyRepository:
    return FakeCompanyRepository()


@pytest.fixture
def mission_repo() -> FakeMissionRepository:
    return FakeMissionRepository()


@pytest.fixture
def product_repo() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def service(
    company_repo: FakeCompanyRepository,
    mission_repo: FakeMissionRepository,
    product_repo: FakeProductRepository,
    workspace_id: UUID,
    other_workspace_id: UUID,
) -> CompanyService:
    workspace_repo = FakeWorkspaceRepository({workspace_id, other_workspace_id})
    return CompanyService(
        company_repository=company_repo,
        workspace_repository=workspace_repo,
        mission_repository=mission_repo,
        product_repository=product_repo,
    )


def _create_payload(workspace_id: UUID, **overrides: object) -> CompanyCreate:
    return CompanyCreate(
        workspace_id=workspace_id,
        mission_id=overrides.get("mission_id"),  # type: ignore[arg-type]
        name=overrides.get("name", "Acme Corp"),  # type: ignore[arg-type]
        website=overrides.get("website"),  # type: ignore[arg-type]
        domain=overrides.get("domain"),  # type: ignore[arg-type]
        industry=overrides.get("industry"),  # type: ignore[arg-type]
        funding_stage=overrides.get("funding_stage"),  # type: ignore[arg-type]
        company_size=overrides.get("company_size"),  # type: ignore[arg-type]
        headquarters_country=overrides.get("headquarters_country"),  # type: ignore[arg-type]
        health_score=overrides.get("health_score"),  # type: ignore[arg-type]
        fit_score=overrides.get("fit_score"),  # type: ignore[arg-type]
        engagement_score=overrides.get("engagement_score"),  # type: ignore[arg-type]
        confidence_score=overrides.get("confidence_score"),  # type: ignore[arg-type]
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_company(
    service: CompanyService, company_repo: FakeCompanyRepository, workspace_id: UUID
) -> None:
    company = await service.create(_create_payload(workspace_id, name="Enterprise Co"))

    assert company.id is not None
    assert company.name == "Enterprise Co"
    assert company.workspace_id == workspace_id
    assert company.status == CompanyStatus.NEW
    assert company_repo.commits == 1


@pytest.mark.asyncio
async def test_create_company_workspace_not_found(service: CompanyService) -> None:
    with pytest.raises(CompanyWorkspaceNotFoundError):
        await service.create(_create_payload(uuid4()))


@pytest.mark.asyncio
async def test_get_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    fetched = await service.get(created.id)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_company_not_found(service: CompanyService) -> None:
    with pytest.raises(CompanyNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_update_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    updated = await service.update(created.id, CompanyUpdate(name="Renamed Co"))
    assert updated.name == "Renamed Co"


@pytest.mark.asyncio
async def test_cannot_update_archived_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    await service.archive(created.id)

    with pytest.raises(CompanyBusinessRuleError, match="archived"):
        await service.update(created.id, CompanyUpdate(name="New Name"))


# ── Website/domain normalization ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_website_normalized_to_canonical_form(service: CompanyService, workspace_id: UUID) -> None:
    company = await service.create(
        _create_payload(workspace_id, website="HTTPS://WWW.Acme.com/about-us?ref=x")
    )
    assert company.domain == "acme.com"
    assert company.website == "https://acme.com"


@pytest.mark.asyncio
async def test_domain_only_input_derives_website(service: CompanyService, workspace_id: UUID) -> None:
    company = await service.create(_create_payload(workspace_id, domain="www.Example.IO"))
    assert company.domain == "example.io"
    assert company.website == "https://example.io"


@pytest.mark.asyncio
async def test_no_web_presence_leaves_both_null(service: CompanyService, workspace_id: UUID) -> None:
    company = await service.create(_create_payload(workspace_id, name="No Website Co"))
    assert company.domain is None
    assert company.website is None


# ── Duplicate domain detection ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_duplicate_domain_within_workspace_rejected(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="Acme", website="https://acme.com"))

    with pytest.raises(CompanyDuplicateDomainError):
        await service.create(_create_payload(workspace_id, name="Acme Duplicate", website="https://acme.com"))


@pytest.mark.asyncio
async def test_duplicate_domain_different_formatting_still_caught(
    service: CompanyService, workspace_id: UUID
) -> None:
    await service.create(_create_payload(workspace_id, name="Acme", website="https://acme.com"))

    with pytest.raises(CompanyDuplicateDomainError):
        await service.create(
            _create_payload(workspace_id, name="Acme Again", website="http://WWW.ACME.COM/")
        )


@pytest.mark.asyncio
async def test_same_domain_allowed_across_workspaces(
    service: CompanyService, workspace_id: UUID, other_workspace_id: UUID
) -> None:
    a = await service.create(_create_payload(workspace_id, website="https://acme.com"))
    b = await service.create(_create_payload(other_workspace_id, website="https://acme.com"))
    assert a.id != b.id


@pytest.mark.asyncio
async def test_multiple_companies_without_domain_allowed(service: CompanyService, workspace_id: UUID) -> None:
    a = await service.create(_create_payload(workspace_id, name="No Domain A"))
    b = await service.create(_create_payload(workspace_id, name="No Domain B"))
    assert a.id != b.id  # no domain means no uniqueness constraint triggers


@pytest.mark.asyncio
async def test_update_to_duplicate_domain_rejected(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="Taken", website="https://taken.com"))
    other = await service.create(_create_payload(workspace_id, name="Other", website="https://other.com"))

    with pytest.raises(CompanyDuplicateDomainError):
        await service.update(other.id, CompanyUpdate(website="https://taken.com"))


@pytest.mark.asyncio
async def test_update_keeping_same_domain_allowed(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id, website="https://acme.com"))
    updated = await service.update(created.id, CompanyUpdate(website="https://acme.com", name="Renamed"))
    assert updated.domain == "acme.com"
    assert updated.name == "Renamed"


# ── Mission/workspace validation ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mission_must_belong_to_workspace(
    service: CompanyService,
    mission_repo: FakeMissionRepository,
    product_repo: FakeProductRepository,
    workspace_id: UUID,
    other_workspace_id: UUID,
) -> None:
    foreign_product_id = uuid4()
    product_repo.register(foreign_product_id, other_workspace_id)
    foreign_mission_id = uuid4()
    mission_repo.register(foreign_mission_id, foreign_product_id)

    with pytest.raises(CompanyMissionNotFoundError):
        await service.create(_create_payload(workspace_id, mission_id=foreign_mission_id))


@pytest.mark.asyncio
async def test_mission_belonging_to_workspace_accepted(
    service: CompanyService,
    mission_repo: FakeMissionRepository,
    product_repo: FakeProductRepository,
    workspace_id: UUID,
) -> None:
    product_id = uuid4()
    product_repo.register(product_id, workspace_id)
    mission_id = uuid4()
    mission_repo.register(mission_id, product_id)

    company = await service.create(_create_payload(workspace_id, mission_id=mission_id))
    assert company.mission_id == mission_id


@pytest.mark.asyncio
async def test_nonexistent_mission_rejected(service: CompanyService, workspace_id: UUID) -> None:
    with pytest.raises(CompanyMissionNotFoundError):
        await service.create(_create_payload(workspace_id, mission_id=uuid4()))


@pytest.mark.asyncio
async def test_mission_optional(service: CompanyService, workspace_id: UUID) -> None:
    company = await service.create(_create_payload(workspace_id))
    assert company.mission_id is None


# ── Score validation ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_valid_scores_accepted(service: CompanyService, workspace_id: UUID) -> None:
    company = await service.create(
        _create_payload(workspace_id, health_score=80, fit_score=90, engagement_score=50, confidence_score=70)
    )
    assert company.fit_score == 90


def test_score_out_of_range_rejected_by_schema(workspace_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        CompanyCreate(workspace_id=workspace_id, name="Bad Score", fit_score=101)


def test_negative_score_rejected_by_schema(workspace_id: UUID = uuid4()) -> None:
    with pytest.raises(ValueError):
        CompanyCreate(workspace_id=workspace_id, name="Bad Score", health_score=-1)


@pytest.mark.asyncio
async def test_update_scores_convenience_method(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    updated = await service.update_scores(created.id, fit_score=85, confidence_score=60)
    assert updated.fit_score == 85
    assert updated.confidence_score == 60


# ── Archive / Restore ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    archived = await service.archive(created.id)
    assert archived.status == CompanyStatus.ARCHIVED


@pytest.mark.asyncio
async def test_cannot_archive_already_archived_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    await service.archive(created.id)

    with pytest.raises(CompanyInvalidTransitionError):
        await service.archive(created.id)


@pytest.mark.asyncio
async def test_restore_archived_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    await service.archive(created.id)

    restored = await service.restore(created.id)
    assert restored.status == CompanyStatus.NEW


@pytest.mark.asyncio
async def test_cannot_restore_non_archived_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))

    with pytest.raises(CompanyInvalidTransitionError):
        await service.restore(created.id)


@pytest.mark.asyncio
async def test_qualify_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    qualified = await service.qualify(created.id)
    assert qualified.status == CompanyStatus.QUALIFIED


@pytest.mark.asyncio
async def test_cannot_qualify_archived_company(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    await service.archive(created.id)

    with pytest.raises(CompanyInvalidTransitionError):
        await service.qualify(created.id)


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    assert created.deleted_at is None

    await service.delete(created.id)
    assert created.deleted_at is not None


@pytest.mark.asyncio
async def test_soft_deleted_company_excluded_from_list(service: CompanyService, workspace_id: UUID) -> None:
    keep = await service.create(_create_payload(workspace_id, name="Keep"))
    delete_me = await service.create(_create_payload(workspace_id, name="Delete", website="https://delete.com"))
    await service.delete(delete_me.id)

    companies, total = await service.list(workspace_id=workspace_id)
    assert total == 1
    assert companies[0].id == keep.id


@pytest.mark.asyncio
async def test_soft_deleted_company_not_found_by_id(service: CompanyService, workspace_id: UUID) -> None:
    created = await service.create(_create_payload(workspace_id))
    await service.delete(created.id)

    with pytest.raises(CompanyNotFoundError):
        await service.get(created.id)


# ── Workspace isolation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_company_workspace_isolation(
    service: CompanyService, workspace_id: UUID, other_workspace_id: UUID
) -> None:
    await service.create(_create_payload(workspace_id, name="Workspace A Co"))
    await service.create(_create_payload(other_workspace_id, name="Workspace B Co"))

    companies_a, total_a = await service.list(workspace_id=workspace_id)
    companies_b, total_b = await service.list(workspace_id=other_workspace_id)

    assert total_a == 1
    assert total_b == 1
    assert companies_a[0].name == "Workspace A Co"
    assert companies_b[0].name == "Workspace B Co"


# ── Search & filters ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_by_name(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="Enterprise Solutions"))
    await service.create(_create_payload(workspace_id, name="SMB Tools"))

    results, total = await service.list(workspace_id=workspace_id, search="Enterprise")
    assert total == 1
    assert results[0].name == "Enterprise Solutions"


@pytest.mark.asyncio
async def test_search_by_domain(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="A", website="https://uniquedomain.com"))
    await service.create(_create_payload(workspace_id, name="B", website="https://other.com"))

    results, total = await service.list(workspace_id=workspace_id, search="uniquedomain")
    assert total == 1
    assert results[0].name == "A"


@pytest.mark.asyncio
async def test_filter_by_industry(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="Tech Co", industry="Software"))
    await service.create(_create_payload(workspace_id, name="Retail Co", industry="Retail"))

    results, total = await service.list(workspace_id=workspace_id, industry="Software")
    assert total == 1
    assert results[0].name == "Tech Co"


@pytest.mark.asyncio
async def test_filter_by_funding_stage(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="Seed Co", funding_stage=FundingStage.SEED))
    await service.create(_create_payload(workspace_id, name="Series A Co", funding_stage=FundingStage.SERIES_A))

    results, total = await service.list(workspace_id=workspace_id, funding_stage=FundingStage.SEED)
    assert total == 1
    assert results[0].name == "Seed Co"


@pytest.mark.asyncio
async def test_filter_by_country(service: CompanyService, workspace_id: UUID) -> None:
    await service.create(_create_payload(workspace_id, name="US Co", headquarters_country="United States"))
    await service.create(_create_payload(workspace_id, name="UK Co", headquarters_country="United Kingdom"))

    results, total = await service.list(workspace_id=workspace_id, country="United States")
    assert total == 1
    assert results[0].name == "US Co"


# ── Pagination ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pagination(service: CompanyService, workspace_id: UUID) -> None:
    for i in range(5):
        await service.create(_create_payload(workspace_id, name=f"Company {i}"))

    page1, total = await service.list(workspace_id=workspace_id, offset=0, limit=2)
    page2, _ = await service.list(workspace_id=workspace_id, offset=2, limit=2)
    page3, _ = await service.list(workspace_id=workspace_id, offset=4, limit=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1
