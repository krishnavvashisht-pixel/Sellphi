from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.models.product import Product, ProductStatus
from app.models.workspace import Workspace, WorkspacePlan, WorkspaceStatus
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product import (
    ProductBusinessRuleError,
    ProductService,
    ProductSlugConflictError,
    ProductWorkspaceNotFoundError,
)


class FakeProductRepository:
    def __init__(self, products: list[Product] | None = None) -> None:
        self.products = products or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, product: Product) -> Product:
        self._hydrate(product)
        self.products.append(product)
        return product

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        filtered = [
            product
            for product in self.products
            if product.workspace_id == workspace_id and product.deleted_at is None
        ]

        if search:
            query = search.lower()
            filtered = [
                product
                for product in filtered
                if query in product.name.lower()
                or query in product.slug.lower()
                or (product.description is not None and query in product.description.lower())
                or (product.category is not None and query in product.category.lower())
            ]

        return filtered[offset : offset + limit], len(filtered)

    async def get_by_id(
        self,
        product_id: UUID,
        workspace_id: UUID | None = None,
    ) -> Product | None:
        return next(
            (
                product
                for product in self.products
                if product.id == product_id
                and product.deleted_at is None
                and (workspace_id is None or product.workspace_id == workspace_id)
            ),
            None,
        )

    async def get_by_slug(self, workspace_id: UUID, slug: str) -> Product | None:
        return next(
            (
                product
                for product in self.products
                if product.workspace_id == workspace_id
                and product.slug == slug
                and product.deleted_at is None
            ),
            None,
        )

    async def update(self, product: Product) -> Product:
        product.updated_at = datetime.now(UTC)
        return product

    async def soft_delete(self, product: Product) -> Product:
        return product

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, product: Product) -> None:
        now = datetime.now(UTC)
        product.id = uuid4()
        product.created_at = now
        product.updated_at = now
        product.deleted_at = None
        product.is_deleted = False


class FakeWorkspaceRepository:
    def __init__(self, workspace_ids: set[UUID]) -> None:
        self.workspace_ids = workspace_ids

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        if workspace_id not in self.workspace_ids:
            return None

        now = datetime.now(UTC)
        workspace = Workspace(
            name="Workspace",
            slug=f"workspace-{workspace_id.hex[:8]}",
            plan=WorkspacePlan.FREE,
            status=WorkspaceStatus.ACTIVE,
            settings={},
        )
        workspace.id = workspace_id
        workspace.created_at = now
        workspace.updated_at = now
        workspace.deleted_at = None
        workspace.is_deleted = False
        return workspace


def make_product(
    *,
    workspace_id: UUID,
    slug: str = "existing-product",
    name: str = "Existing Product",
    category: str | None = "sales",
) -> Product:
    now = datetime.now(UTC)
    product = Product(
        workspace_id=workspace_id,
        name=name,
        slug=slug,
        description="Revenue intelligence platform",
        website="https://example.com",
        category=category,
        status=ProductStatus.DRAFT,
        settings={},
    )
    product.id = uuid4()
    product.created_at = now
    product.updated_at = now
    product.deleted_at = None
    product.is_deleted = False
    return product


def make_service(
    *,
    workspace_ids: set[UUID],
    products: list[Product] | None = None,
) -> tuple[ProductService, FakeProductRepository]:
    product_repository = FakeProductRepository(products)
    workspace_repository = FakeWorkspaceRepository(workspace_ids)
    return (
        ProductService(
            product_repository=product_repository,
            workspace_repository=workspace_repository,
        ),
        product_repository,
    )


@pytest.mark.asyncio
async def test_create_product_generates_slug() -> None:
    workspace_id = uuid4()
    service, repository = make_service(workspace_ids={workspace_id})

    product = await service.create(
        ProductCreate(
            workspace_id=workspace_id,
            name="Revenue Intelligence",
            website="https://sellphi.example",
        )
    )

    assert product.slug == "revenue-intelligence"
    assert product.status == ProductStatus.DRAFT
    assert repository.commits == 1


@pytest.mark.asyncio
async def test_create_product_requires_existing_workspace() -> None:
    service, _repository = make_service(workspace_ids=set())

    with pytest.raises(ProductWorkspaceNotFoundError):
        await service.create(ProductCreate(workspace_id=uuid4(), name="Revenue Intelligence"))


@pytest.mark.asyncio
async def test_duplicate_slug_is_scoped_to_workspace() -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    existing = make_product(workspace_id=workspace_id, slug="revenue-intelligence")
    same_slug_elsewhere = make_product(
        workspace_id=other_workspace_id,
        slug="revenue-intelligence",
    )
    service, _repository = make_service(
        workspace_ids={workspace_id, other_workspace_id},
        products=[existing, same_slug_elsewhere],
    )

    with pytest.raises(ProductSlugConflictError):
        await service.create(
            ProductCreate(
                workspace_id=workspace_id,
                name="Revenue Intelligence",
                slug="revenue-intelligence",
            )
        )

    product = await service.create(
        ProductCreate(
            workspace_id=other_workspace_id,
            name="Another Product",
            slug="another-product",
        )
    )
    assert product.workspace_id == other_workspace_id


@pytest.mark.asyncio
async def test_list_products_supports_pagination_and_workspace_isolation() -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    products = [
        make_product(workspace_id=workspace_id, slug="one", name="One"),
        make_product(workspace_id=workspace_id, slug="two", name="Two"),
        make_product(workspace_id=workspace_id, slug="three", name="Three"),
        make_product(workspace_id=other_workspace_id, slug="outside", name="Outside"),
    ]
    service, _repository = make_service(
        workspace_ids={workspace_id, other_workspace_id},
        products=products,
    )

    page, total = await service.list(workspace_id=workspace_id, offset=1, limit=1)

    assert total == 3
    assert len(page) == 1
    assert page[0].workspace_id == workspace_id
    assert page[0].slug == "two"


@pytest.mark.asyncio
async def test_list_products_supports_search() -> None:
    workspace_id = uuid4()
    products = [
        make_product(
            workspace_id=workspace_id,
            slug="revenue-intelligence",
            name="Revenue Intelligence",
            category="sales",
        ),
        make_product(
            workspace_id=workspace_id,
            slug="support-hub",
            name="Support Hub",
            category="service",
        ),
    ]
    service, _repository = make_service(workspace_ids={workspace_id}, products=products)

    page, total = await service.list(workspace_id=workspace_id, search="support")

    assert total == 1
    assert page[0].slug == "support-hub"


@pytest.mark.asyncio
async def test_update_product_rejects_archived_reactivation() -> None:
    workspace_id = uuid4()
    product = make_product(workspace_id=workspace_id)
    product.status = ProductStatus.ARCHIVED
    service, _repository = make_service(workspace_ids={workspace_id}, products=[product])

    with pytest.raises(ProductBusinessRuleError):
        await service.update(product.id, ProductUpdate(status=ProductStatus.ACTIVE))


@pytest.mark.asyncio
async def test_delete_product_soft_deletes() -> None:
    workspace_id = uuid4()
    product = make_product(workspace_id=workspace_id)
    service, repository = make_service(workspace_ids={workspace_id}, products=[product])

    await service.delete(product.id)

    assert product.deleted_at is not None
    assert repository.commits == 1
