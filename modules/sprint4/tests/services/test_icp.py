from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.models.icp import ICP
from app.models.product import Product, ProductStatus
from app.schemas.icp import ICPCreate, ICPUpdate
from app.services.icp import (
    ICPBusinessRuleError,
    ICPNotFoundError,
    ICPProductNotFoundError,
    ICPService,
)


# ── Fake repositories ─────────────────────────────────────────────────────────

class FakeICPRepository:
    def __init__(self, icps: list[ICP] | None = None) -> None:
        self.icps = icps or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, icp: ICP) -> ICP:
        self._hydrate(icp)
        self.icps.append(icp)
        return icp

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[ICP], int]:
        filtered = [
            i for i in self.icps
            if i.product_id == product_id and i.deleted_at is None
        ]
        if is_active is not None:
            filtered = [i for i in filtered if i.is_active == is_active]
        if search:
            q = search.lower()
            filtered = [
                i for i in filtered
                if q in i.name.lower()
                or (i.description is not None and q in i.description.lower())
            ]
        return filtered[offset: offset + limit], len(filtered)

    async def get_by_id(self, icp_id: UUID, product_id: UUID | None = None) -> ICP | None:
        return next(
            (
                i for i in self.icps
                if i.id == icp_id
                and i.deleted_at is None
                and (product_id is None or i.product_id == product_id)
            ),
            None,
        )

    async def get_default_for_product(self, product_id: UUID) -> ICP | None:
        return next(
            (i for i in self.icps if i.product_id == product_id and i.is_default and i.deleted_at is None),
            None,
        )

    async def get_active_defaults_for_product(self, product_id: UUID) -> list[ICP]:
        return [i for i in self.icps if i.product_id == product_id and i.is_default and i.deleted_at is None]

    async def update(self, icp: ICP) -> ICP:
        icp.updated_at = datetime.now(UTC)
        return icp

    async def soft_delete(self, icp: ICP) -> ICP:
        return icp

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, icp: ICP) -> None:
        now = datetime.now(UTC)
        icp.id = uuid4()
        icp.created_at = now
        icp.updated_at = now
        icp.deleted_at = None
        icp.is_deleted = False


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
def icp_repo() -> FakeICPRepository:
    return FakeICPRepository()


@pytest.fixture
def service(icp_repo: FakeICPRepository, product_id: UUID) -> ICPService:
    product_repo = FakeProductRepository({product_id})
    return ICPService(icp_repository=icp_repo, product_repository=product_repo)


def _create_payload(product_id: UUID, **overrides: object) -> ICPCreate:
    return ICPCreate(
        product_id=product_id,
        name=overrides.get("name", "Mid-Market SaaS"),  # type: ignore[arg-type]
        description=overrides.get("description", "Companies with 50-500 employees"),  # type: ignore[arg-type]
        employee_range_min=overrides.get("employee_range_min"),  # type: ignore[arg-type]
        employee_range_max=overrides.get("employee_range_max"),  # type: ignore[arg-type]
        annual_revenue_min=overrides.get("annual_revenue_min"),  # type: ignore[arg-type]
        annual_revenue_max=overrides.get("annual_revenue_max"),  # type: ignore[arg-type]
        is_default=overrides.get("is_default", False),  # type: ignore[arg-type]
        is_active=overrides.get("is_active", True),  # type: ignore[arg-type]
        industries=overrides.get("industries", []),  # type: ignore[arg-type]
        countries=overrides.get("countries", []),  # type: ignore[arg-type]
        states=overrides.get("states", []),  # type: ignore[arg-type]
        cities=overrides.get("cities", []),  # type: ignore[arg-type]
        technologies=overrides.get("technologies", []),  # type: ignore[arg-type]
        funding_stages=overrides.get("funding_stages", []),  # type: ignore[arg-type]
        growth_signals=overrides.get("growth_signals", []),  # type: ignore[arg-type]
        keywords=overrides.get("keywords", []),  # type: ignore[arg-type]
        negative_keywords=overrides.get("negative_keywords", []),  # type: ignore[arg-type]
        scoring_rules=overrides.get("scoring_rules", {}),  # type: ignore[arg-type]
    )


# ── CRUD tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_icp(service: ICPService, icp_repo: FakeICPRepository, product_id: UUID) -> None:
    payload = _create_payload(product_id, name="Enterprise SaaS")
    icp = await service.create(payload)

    assert icp.id is not None
    assert icp.name == "Enterprise SaaS"
    assert icp.product_id == product_id
    assert icp.is_default is False
    assert icp.is_active is True
    assert icp_repo.commits == 1


@pytest.mark.asyncio
async def test_get_icp(service: ICPService, product_id: UUID) -> None:
    payload = _create_payload(product_id)
    created = await service.create(payload)

    fetched = await service.get(created.id)
    assert fetched.id == created.id
    assert fetched.name == created.name


@pytest.mark.asyncio
async def test_get_icp_not_found(service: ICPService) -> None:
    with pytest.raises(ICPNotFoundError):
        await service.get(uuid4())


@pytest.mark.asyncio
async def test_list_icps(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="ICP A"))
    await service.create(_create_payload(product_id, name="ICP B"))

    icps, total = await service.list(product_id=product_id)
    assert total == 2
    assert len(icps) == 2


@pytest.mark.asyncio
async def test_update_icp(service: ICPService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))

    updated = await service.update(created.id, ICPUpdate(name="Updated Name"))
    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_soft_delete_icp(service: ICPService, icp_repo: FakeICPRepository, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id))
    await service.delete(created.id)

    # Should be gone from queries
    fetched = await icp_repo.get_by_id(created.id)
    assert fetched is None or fetched.deleted_at is not None


# ── Validation tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_invalid_employee_range(service: ICPService, product_id: UUID) -> None:
    with pytest.raises(Exception):  # Pydantic or ICPBusinessRuleError
        await service.create(_create_payload(product_id, employee_range_min=500, employee_range_max=100))


@pytest.mark.asyncio
async def test_create_invalid_revenue_range(service: ICPService, product_id: UUID) -> None:
    with pytest.raises(Exception):
        await service.create(_create_payload(product_id, annual_revenue_min=1_000_000, annual_revenue_max=500_000))


@pytest.mark.asyncio
async def test_update_invalid_employee_range(service: ICPService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id, employee_range_min=10, employee_range_max=100))

    with pytest.raises(ICPBusinessRuleError):
        await service.update(created.id, ICPUpdate(employee_range_min=200))


@pytest.mark.asyncio
async def test_update_invalid_revenue_range(service: ICPService, product_id: UUID) -> None:
    created = await service.create(_create_payload(product_id, annual_revenue_min=100_000, annual_revenue_max=1_000_000))

    with pytest.raises(ICPBusinessRuleError):
        await service.update(created.id, ICPUpdate(annual_revenue_max=50_000))


# ── Product existence validation ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_icp_product_not_found(service: ICPService) -> None:
    with pytest.raises(ICPProductNotFoundError):
        await service.create(_create_payload(uuid4()))  # unknown product_id


@pytest.mark.asyncio
async def test_list_icps_product_not_found(service: ICPService) -> None:
    with pytest.raises(ICPProductNotFoundError):
        await service.list(product_id=uuid4())


@pytest.mark.asyncio
async def test_get_default_product_not_found(service: ICPService) -> None:
    with pytest.raises(ICPProductNotFoundError):
        await service.get_default_for_product(uuid4())


# ── Default ICP logic ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_default_icp(service: ICPService, product_id: UUID) -> None:
    icp = await service.create(_create_payload(product_id, is_default=True))
    assert icp.is_default is True


@pytest.mark.asyncio
async def test_only_one_default_per_product_on_create(
    service: ICPService, icp_repo: FakeICPRepository, product_id: UUID
) -> None:
    first = await service.create(_create_payload(product_id, name="First", is_default=True))
    second = await service.create(_create_payload(product_id, name="Second", is_default=True))

    assert second.is_default is True
    # First should have been demoted
    first_fetched = await icp_repo.get_by_id(first.id)
    assert first_fetched is not None
    assert first_fetched.is_default is False


@pytest.mark.asyncio
async def test_only_one_default_per_product_on_update(
    service: ICPService, icp_repo: FakeICPRepository, product_id: UUID
) -> None:
    first = await service.create(_create_payload(product_id, name="First", is_default=True))
    second = await service.create(_create_payload(product_id, name="Second", is_default=False))

    # Promote second to default
    await service.update(second.id, ICPUpdate(is_default=True))

    first_fetched = await icp_repo.get_by_id(first.id)
    assert first_fetched is not None
    assert first_fetched.is_default is False


@pytest.mark.asyncio
async def test_get_default_icp(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, is_default=True))
    default = await service.get_default_for_product(product_id)
    assert default.is_default is True


@pytest.mark.asyncio
async def test_get_default_icp_not_found(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, is_default=False))
    with pytest.raises(ICPNotFoundError):
        await service.get_default_for_product(product_id)


@pytest.mark.asyncio
async def test_cannot_delete_default_icp(service: ICPService, product_id: UUID) -> None:
    icp = await service.create(_create_payload(product_id, is_default=True))
    with pytest.raises(ICPBusinessRuleError, match="Cannot delete the default ICP"):
        await service.delete(icp.id)


# ── Product isolation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_icp_product_isolation(product_id: UUID, other_product_id: UUID) -> None:
    """ICPs from different products must not bleed into each other's listings."""
    icp_repo = FakeICPRepository()
    product_repo = FakeProductRepository({product_id, other_product_id})
    service = ICPService(icp_repository=icp_repo, product_repository=product_repo)

    await service.create(_create_payload(product_id, name="Product A ICP"))
    await service.create(_create_payload(other_product_id, name="Product B ICP"))

    icps_a, total_a = await service.list(product_id=product_id)
    icps_b, total_b = await service.list(product_id=other_product_id)

    assert total_a == 1
    assert total_b == 1
    assert icps_a[0].name == "Product A ICP"
    assert icps_b[0].name == "Product B ICP"


@pytest.mark.asyncio
async def test_default_icp_isolation(product_id: UUID, other_product_id: UUID) -> None:
    """Default for product A must not affect product B's default."""
    icp_repo = FakeICPRepository()
    product_repo = FakeProductRepository({product_id, other_product_id})
    service = ICPService(icp_repository=icp_repo, product_repository=product_repo)

    icp_a = await service.create(_create_payload(product_id, is_default=True))
    icp_b = await service.create(_create_payload(other_product_id, is_default=True))

    # Both should still be default for their own product
    default_a = await service.get_default_for_product(product_id)
    default_b = await service.get_default_for_product(other_product_id)

    assert default_a.id == icp_a.id
    assert default_b.id == icp_b.id


# ── Pagination tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_pagination_offset(service: ICPService, product_id: UUID) -> None:
    for i in range(5):
        await service.create(_create_payload(product_id, name=f"ICP {i}"))

    page1, total = await service.list(product_id=product_id, offset=0, limit=2)
    page2, _ = await service.list(product_id=product_id, offset=2, limit=2)
    page3, _ = await service.list(product_id=product_id, offset=4, limit=2)

    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    assert len(page3) == 1


@pytest.mark.asyncio
async def test_list_pagination_limit(service: ICPService, product_id: UUID) -> None:
    for i in range(10):
        await service.create(_create_payload(product_id, name=f"ICP {i}"))

    icps, total = await service.list(product_id=product_id, limit=3)
    assert total == 10
    assert len(icps) == 3


# ── Search tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_by_name(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Enterprise Buyers"))
    await service.create(_create_payload(product_id, name="SMB Prospects"))

    results, total = await service.list(product_id=product_id, search="Enterprise")
    assert total == 1
    assert results[0].name == "Enterprise Buyers"


@pytest.mark.asyncio
async def test_search_by_description(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="ICP A", description="Funded startups in fintech"))
    await service.create(_create_payload(product_id, name="ICP B", description="Large insurance companies"))

    results, total = await service.list(product_id=product_id, search="fintech")
    assert total == 1
    assert results[0].name == "ICP A"


@pytest.mark.asyncio
async def test_search_case_insensitive(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="MidMarket SaaS"))

    results, _ = await service.list(product_id=product_id, search="midmarket")
    assert len(results) == 1

    results, _ = await service.list(product_id=product_id, search="MIDMARKET")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_no_match(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Enterprise"))
    results, total = await service.list(product_id=product_id, search="nonexistent")
    assert total == 0
    assert results == []


# ── Soft delete tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(
    service: ICPService, icp_repo: FakeICPRepository, product_id: UUID
) -> None:
    icp = await service.create(_create_payload(product_id))
    assert icp.deleted_at is None

    await service.delete(icp.id)
    assert icp.deleted_at is not None
    assert icp.is_active is False


@pytest.mark.asyncio
async def test_soft_deleted_icp_excluded_from_list(
    service: ICPService, product_id: UUID
) -> None:
    icp_a = await service.create(_create_payload(product_id, name="Keep"))
    icp_b = await service.create(_create_payload(product_id, name="Delete"))
    await service.delete(icp_b.id)

    icps, total = await service.list(product_id=product_id)
    assert total == 1
    assert icps[0].id == icp_a.id


@pytest.mark.asyncio
async def test_soft_deleted_icp_not_found_by_id(
    service: ICPService, product_id: UUID
) -> None:
    icp = await service.create(_create_payload(product_id))
    await service.delete(icp.id)

    with pytest.raises(ICPNotFoundError):
        await service.get(icp.id)


# ── is_active filter ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_filter_active_only(service: ICPService, product_id: UUID) -> None:
    await service.create(_create_payload(product_id, name="Active ICP", is_active=True))
    inactive = await service.create(_create_payload(product_id, name="Inactive ICP", is_active=False))

    active_list, total = await service.list(product_id=product_id, is_active=True)
    assert total == 1
    assert all(i.is_active for i in active_list)

    inactive_list, total = await service.list(product_id=product_id, is_active=False)
    assert total == 1
    assert inactive_list[0].id == inactive.id
