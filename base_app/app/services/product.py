import re
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityConflictError,
    EntityNotFoundError,
)
from app.models.product import Product, ProductStatus
from app.repositories.product import ProductRepository
from app.repositories.workspace import WorkspaceRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.time import utc_now

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProductNotFoundError(EntityNotFoundError):
    error_code = "product_not_found"


class ProductWorkspaceNotFoundError(EntityNotFoundError):
    error_code = "product_workspace_not_found"


class ProductSlugConflictError(EntityConflictError):
    error_code = "product_slug_conflict"


class ProductBusinessRuleError(BusinessRuleViolationError):
    error_code = "product_business_rule_violation"


class ProductService:
    def __init__(
        self,
        product_repository: ProductRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._product_repository = product_repository
        self._workspace_repository = workspace_repository

    async def create(self, payload: ProductCreate) -> Product:
        await self._ensure_workspace_exists(payload.workspace_id)
        slug = self._normalize_slug(payload.slug or self._slugify(payload.name))
        await self._ensure_slug_available(payload.workspace_id, slug)
        self._validate_status_transition(None, payload.status)

        product = Product(
            workspace_id=payload.workspace_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            website=str(payload.website) if payload.website is not None else None,
            category=payload.category,
            status=payload.status,
            settings=payload.settings,
        )

        try:
            created = await self._product_repository.create(product)
            await self._product_repository.commit()
        except Exception:
            await self._product_repository.rollback()
            raise

        return created

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        await self._ensure_workspace_exists(workspace_id)
        return await self._product_repository.list(
            workspace_id=workspace_id,
            offset=offset,
            limit=limit,
            search=search,
        )

    async def get(self, product_id: UUID, workspace_id: UUID | None = None) -> Product:
        product = await self._product_repository.get_by_id(product_id, workspace_id=workspace_id)
        if product is None:
            raise ProductNotFoundError("Product not found")
        return product

    async def update(self, product_id: UUID, payload: ProductUpdate) -> Product:
        product = await self.get(product_id)
        updates = payload.model_dump(exclude_unset=True)

        if "slug" in updates:
            next_slug = self._normalize_slug(updates["slug"])
            if next_slug != product.slug:
                await self._ensure_slug_available(
                    product.workspace_id,
                    next_slug,
                    exclude_id=product.id,
                )
            product.slug = next_slug

        if "name" in updates:
            product.name = updates["name"]

        if "description" in updates:
            product.description = updates["description"]

        if "website" in updates:
            website = updates["website"]
            product.website = str(website) if website is not None else None

        if "category" in updates:
            product.category = updates["category"]

        if "status" in updates:
            self._validate_status_transition(product.status, updates["status"])
            product.status = updates["status"]

        if "settings" in updates:
            product.settings = updates["settings"]

        try:
            updated = await self._product_repository.update(product)
            await self._product_repository.commit()
        except Exception:
            await self._product_repository.rollback()
            raise

        return updated

    async def delete(self, product_id: UUID) -> None:
        product = await self.get(product_id)
        product.deleted_at = utc_now()

        try:
            await self._product_repository.soft_delete(product)
            await self._product_repository.commit()
        except Exception:
            await self._product_repository.rollback()
            raise

    async def _ensure_workspace_exists(self, workspace_id: UUID) -> None:
        workspace = await self._workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise ProductWorkspaceNotFoundError("Workspace not found")

    async def _ensure_slug_available(
        self,
        workspace_id: UUID,
        slug: str,
        exclude_id: UUID | None = None,
    ) -> None:
        existing = await self._product_repository.get_by_slug(workspace_id, slug)
        if existing is not None and existing.id != exclude_id:
            raise ProductSlugConflictError("Product slug already exists in this workspace")

    def _normalize_slug(self, slug: str) -> str:
        normalized = self._slugify(slug)
        if not normalized or not SLUG_PATTERN.fullmatch(normalized):
            raise ProductBusinessRuleError(
                "Product slug must contain lowercase letters, numbers, and hyphens"
            )
        return normalized

    def _slugify(self, value: str) -> str:
        lowered = value.strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", lowered)
        return slug.strip("-")

    def _validate_status_transition(
        self,
        current_status: ProductStatus | None,
        next_status: ProductStatus,
    ) -> None:
        if current_status == ProductStatus.ARCHIVED and next_status != ProductStatus.ARCHIVED:
            raise ProductBusinessRuleError("Archived products cannot be reactivated")
