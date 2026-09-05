from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.icp import ICP


class ICPRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, icp: ICP) -> ICP:
        self._session.add(icp)
        await self._session.flush()
        await self._session.refresh(icp)
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
        statement = self._base_list_statement(
            product_id=product_id,
            search=search,
            is_active=is_active,
        )
        count_statement = select(func.count()).select_from(statement.subquery())

        icps_result = await self._session.execute(
            statement.order_by(ICP.is_default.desc(), ICP.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(icps_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(self, icp_id: UUID, product_id: UUID | None = None) -> ICP | None:
        filters = [ICP.id == icp_id, ICP.deleted_at.is_(None)]
        if product_id is not None:
            filters.append(ICP.product_id == product_id)

        statement = select(ICP).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_default_for_product(self, product_id: UUID) -> ICP | None:
        statement = select(ICP).where(
            ICP.product_id == product_id,
            ICP.is_default.is_(True),
            ICP.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_defaults_for_product(self, product_id: UUID) -> list[ICP]:
        """Returns all non-deleted default ICPs for a product (used to enforce uniqueness)."""
        statement = select(ICP).where(
            ICP.product_id == product_id,
            ICP.is_default.is_(True),
            ICP.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def update(self, icp: ICP) -> ICP:
        await self._session.flush()
        await self._session.refresh(icp)
        return icp

    async def soft_delete(self, icp: ICP) -> ICP:
        await self._session.flush()
        await self._session.refresh(icp)
        return icp

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        product_id: UUID,
        search: str | None,
        is_active: bool | None,
    ) -> Select[tuple[ICP]]:
        statement = select(ICP).where(
            ICP.product_id == product_id,
            ICP.deleted_at.is_(None),
        )

        if is_active is not None:
            statement = statement.where(ICP.is_active.is_(is_active))

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    ICP.name.ilike(query),
                    ICP.description.ilike(query),
                )
            )

        return statement
