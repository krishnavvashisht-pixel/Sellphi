from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, product: Product) -> Product:
        self._session.add(product)
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        statement = self._base_list_statement(workspace_id=workspace_id, search=search)
        count_statement = select(func.count()).select_from(statement.subquery())

        products_result = await self._session.execute(
            statement.order_by(Product.created_at.desc()).offset(offset).limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(products_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(self, product_id: UUID, workspace_id: UUID | None = None) -> Product | None:
        filters = [Product.id == product_id, Product.deleted_at.is_(None)]
        if workspace_id is not None:
            filters.append(Product.workspace_id == workspace_id)

        statement = select(Product).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_slug(self, workspace_id: UUID, slug: str) -> Product | None:
        statement = select(Product).where(
            Product.workspace_id == workspace_id,
            Product.slug == slug,
            Product.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, product: Product) -> Product:
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def soft_delete(self, product: Product) -> Product:
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        workspace_id: UUID,
        search: str | None,
    ) -> Select[tuple[Product]]:
        statement = select(Product).where(
            Product.workspace_id == workspace_id,
            Product.deleted_at.is_(None),
        )

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Product.name.ilike(query),
                    Product.slug.ilike(query),
                    Product.description.ilike(query),
                    Product.category.ilike(query),
                )
            )

        return statement
