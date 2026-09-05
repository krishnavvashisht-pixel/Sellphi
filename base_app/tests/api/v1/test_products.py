from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.api.v1.products.routes import get_product_service
from app.main import app
from app.models.product import ProductStatus
from app.schemas.product import ProductCreate, ProductUpdate
from httpx import AsyncClient


class FakeProductService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.product_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: ProductCreate) -> object:
        return self._product(
            workspace_id=payload.workspace_id,
            name=payload.name,
            slug=payload.slug or "revenue-intelligence",
            description=payload.description,
            website=str(payload.website) if payload.website is not None else None,
            category=payload.category,
            status=payload.status,
            settings=payload.settings,
        )

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[object], int]:
        return [self._product(workspace_id=workspace_id)], 1

    async def get(self, product_id: UUID) -> object:
        return self._product(product_id=product_id)

    async def update(self, product_id: UUID, payload: ProductUpdate) -> object:
        return self._product(
            product_id=product_id,
            name=payload.name or "Updated Product",
            slug=payload.slug or "updated-product",
            status=payload.status or ProductStatus.ACTIVE,
            settings=payload.settings or {"tone": "direct"},
        )

    async def delete(self, product_id: UUID) -> None:
        self.deleted_ids.append(product_id)

    def _product(
        self,
        *,
        product_id: UUID | None = None,
        workspace_id: UUID | None = None,
        name: str = "Revenue Intelligence",
        slug: str = "revenue-intelligence",
        description: str | None = "Pipeline acceleration product",
        website: str | None = "https://sellphi.example",
        category: str | None = "sales",
        status: ProductStatus = ProductStatus.DRAFT,
        settings: dict[str, object] | None = None,
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=product_id or self.product_id,
            workspace_id=workspace_id or self.workspace_id,
            name=name,
            slug=slug,
            description=description,
            website=website,
            category=category,
            status=status,
            settings=settings or {},
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def product_service() -> FakeProductService:
    service = FakeProductService()
    app.dependency_overrides[get_product_service] = lambda: service
    return service


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, product_service: FakeProductService) -> None:
    response = await client.post(
        "/api/v1/products",
        json={
            "workspace_id": str(product_service.workspace_id),
            "name": "Revenue Intelligence",
            "website": "https://sellphi.example",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["workspace_id"] == str(product_service.workspace_id)
    assert body["slug"] == "revenue-intelligence"
    assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient, product_service: FakeProductService) -> None:
    response = await client.get(
        "/api/v1/products",
        params={"workspace_id": str(product_service.workspace_id), "offset": 0, "limit": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["offset"] == 0
    assert body["limit"] == 10
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_get_product(client: AsyncClient, product_service: FakeProductService) -> None:
    response = await client.get(f"/api/v1/products/{product_service.product_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(product_service.product_id)


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, product_service: FakeProductService) -> None:
    response = await client.patch(
        f"/api/v1/products/{product_service.product_id}",
        json={"name": "Updated Product", "status": "active"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Product"
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, product_service: FakeProductService) -> None:
    response = await client.delete(f"/api/v1/products/{product_service.product_id}")

    assert response.status_code == 204
    assert product_service.deleted_ids == [product_service.product_id]
