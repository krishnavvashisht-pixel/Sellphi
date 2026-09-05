from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.icps.routes import get_icp_service
from app.main import app
from app.schemas.icp import ICPCreate, ICPUpdate
from app.services.icp import ICPBusinessRuleError, ICPNotFoundError, ICPProductNotFoundError


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeICPService:
    def __init__(self) -> None:
        self.product_id = uuid4()
        self.icp_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: ICPCreate) -> object:
        return self._icp(
            product_id=payload.product_id,
            name=payload.name,
            description=payload.description,
            is_default=payload.is_default,
            is_active=payload.is_active,
            employee_range_min=payload.employee_range_min,
            employee_range_max=payload.employee_range_max,
            annual_revenue_min=payload.annual_revenue_min,
            annual_revenue_max=payload.annual_revenue_max,
            industries=payload.industries,
            countries=payload.countries,
            states=payload.states,
            cities=payload.cities,
            technologies=payload.technologies,
            funding_stages=payload.funding_stages,
            growth_signals=payload.growth_signals,
            keywords=payload.keywords,
            negative_keywords=payload.negative_keywords,
            scoring_rules=payload.scoring_rules,
        )

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[object], int]:
        return [self._icp(product_id=product_id)], 1

    async def get(self, icp_id: UUID, product_id: UUID | None = None) -> object:
        return self._icp(icp_id=icp_id)

    async def get_default_for_product(self, product_id: UUID) -> object:
        return self._icp(product_id=product_id, is_default=True)

    async def update(self, icp_id: UUID, payload: ICPUpdate) -> object:
        return self._icp(
            icp_id=icp_id,
            name=payload.name or "Updated ICP",
            is_default=payload.is_default if payload.is_default is not None else False,
        )

    async def delete(self, icp_id: UUID) -> None:
        self.deleted_ids.append(icp_id)

    def _icp(
        self,
        *,
        icp_id: UUID | None = None,
        product_id: UUID | None = None,
        name: str = "Mid-Market SaaS",
        description: str | None = "Target profile",
        is_default: bool = False,
        is_active: bool = True,
        employee_range_min: int | None = 50,
        employee_range_max: int | None = 500,
        annual_revenue_min: int | None = None,
        annual_revenue_max: int | None = None,
        industries: list[str] | None = None,
        countries: list[str] | None = None,
        states: list[str] | None = None,
        cities: list[str] | None = None,
        technologies: list[str] | None = None,
        funding_stages: list[str] | None = None,
        growth_signals: list[str] | None = None,
        keywords: list[str] | None = None,
        negative_keywords: list[str] | None = None,
        scoring_rules: dict | None = None,
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=icp_id or self.icp_id,
            product_id=product_id or self.product_id,
            name=name,
            description=description,
            is_default=is_default,
            is_active=is_active,
            employee_range_min=employee_range_min,
            employee_range_max=employee_range_max,
            annual_revenue_min=annual_revenue_min,
            annual_revenue_max=annual_revenue_max,
            industries=industries or [],
            countries=countries or [],
            states=states or [],
            cities=cities or [],
            technologies=technologies or [],
            funding_stages=funding_stages or [],
            growth_signals=growth_signals or [],
            keywords=keywords or [],
            negative_keywords=negative_keywords or [],
            scoring_rules=scoring_rules or {},
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def icp_service() -> FakeICPService:
    service = FakeICPService()
    app.dependency_overrides[get_icp_service] = lambda: service
    return service


# ── POST /api/v1/icps ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_icp(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.post(
        "/api/v1/icps",
        json={
            "product_id": str(icp_service.product_id),
            "name": "Mid-Market SaaS",
            "description": "Companies with 50-500 employees",
            "employee_range_min": 50,
            "employee_range_max": 500,
            "is_default": False,
            "is_active": True,
            "industries": ["SaaS"],
            "countries": ["US"],
            "states": [],
            "cities": [],
            "technologies": [],
            "funding_stages": [],
            "growth_signals": [],
            "keywords": [],
            "negative_keywords": [],
            "scoring_rules": {},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mid-Market SaaS"
    assert data["product_id"] == str(icp_service.product_id)


@pytest.mark.asyncio
async def test_create_icp_invalid_range_rejected(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.post(
        "/api/v1/icps",
        json={
            "product_id": str(icp_service.product_id),
            "name": "Bad Range",
            "employee_range_min": 500,
            "employee_range_max": 50,  # min > max
            "industries": [],
            "countries": [],
            "states": [],
            "cities": [],
            "technologies": [],
            "funding_stages": [],
            "growth_signals": [],
            "keywords": [],
            "negative_keywords": [],
            "scoring_rules": {},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_icp_product_not_found(client: AsyncClient, icp_service: FakeICPService) -> None:
    async def raise_not_found(payload: ICPCreate) -> None:
        raise ICPProductNotFoundError("Product not found")

    icp_service.create = raise_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/icps",
        json={
            "product_id": str(uuid4()),
            "name": "ICP",
            "industries": [],
            "countries": [],
            "states": [],
            "cities": [],
            "technologies": [],
            "funding_stages": [],
            "growth_signals": [],
            "keywords": [],
            "negative_keywords": [],
            "scoring_rules": {},
        },
    )
    assert response.status_code == 404


# ── GET /api/v1/icps ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_icps(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.get(
        "/api/v1/icps",
        params={"product_id": str(icp_service.product_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_icps_missing_product_id(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.get("/api/v1/icps")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_icps_with_pagination(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.get(
        "/api/v1/icps",
        params={"product_id": str(icp_service.product_id), "offset": 0, "limit": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 0
    assert data["limit"] == 10


# ── GET /api/v1/icps/{id} ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_icp(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.get(f"/api/v1/icps/{icp_service.icp_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(icp_service.icp_id)


@pytest.mark.asyncio
async def test_get_icp_not_found(client: AsyncClient, icp_service: FakeICPService) -> None:
    async def raise_not_found(icp_id: UUID, product_id: UUID | None = None) -> None:
        raise ICPNotFoundError("ICP not found")

    icp_service.get = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/icps/{uuid4()}")
    assert response.status_code == 404


# ── PATCH /api/v1/icps/{id} ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_icp(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.patch(
        f"/api/v1/icps/{icp_service.icp_id}",
        json={"name": "Updated ICP"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated ICP"


@pytest.mark.asyncio
async def test_update_icp_business_rule_error(client: AsyncClient, icp_service: FakeICPService) -> None:
    async def raise_rule_error(icp_id: UUID, payload: ICPUpdate) -> None:
        raise ICPBusinessRuleError("employee_range_min must be <= employee_range_max")

    icp_service.update = raise_rule_error  # type: ignore[method-assign]

    response = await client.patch(
        f"/api/v1/icps/{icp_service.icp_id}",
        json={"employee_range_min": 999},
    )
    assert response.status_code == 422


# ── DELETE /api/v1/icps/{id} ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_icp(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.delete(f"/api/v1/icps/{icp_service.icp_id}")
    assert response.status_code == 204
    assert icp_service.icp_id in icp_service.deleted_ids


@pytest.mark.asyncio
async def test_delete_default_icp_forbidden(client: AsyncClient, icp_service: FakeICPService) -> None:
    async def raise_rule_error(icp_id: UUID) -> None:
        raise ICPBusinessRuleError("Cannot delete the default ICP")

    icp_service.delete = raise_rule_error  # type: ignore[method-assign]

    response = await client.delete(f"/api/v1/icps/{icp_service.icp_id}")
    assert response.status_code == 422


# ── GET /api/v1/products/{id}/default-icp ────────────────────────────────────

@pytest.mark.asyncio
async def test_get_default_icp(client: AsyncClient, icp_service: FakeICPService) -> None:
    response = await client.get(f"/api/v1/products/{icp_service.product_id}/default-icp")
    assert response.status_code == 200
    data = response.json()
    assert data["is_default"] is True
    assert data["product_id"] == str(icp_service.product_id)


@pytest.mark.asyncio
async def test_get_default_icp_not_found(client: AsyncClient, icp_service: FakeICPService) -> None:
    async def raise_not_found(product_id: UUID) -> None:
        raise ICPNotFoundError("No default ICP found for this product")

    icp_service.get_default_for_product = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/products/{uuid4()}/default-icp")
    assert response.status_code == 404
