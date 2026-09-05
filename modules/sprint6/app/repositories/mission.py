from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mission import Mission, MissionStatus


class MissionRepository:
    """
    Pure data-access layer: CRUD, pagination, search, and product/status
    filtering only. No business rules live here — see MissionService.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, mission: Mission) -> Mission:
        self._session.add(mission)
        await self._session.flush()
        await self._session.refresh(mission)
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
        statement = self._base_list_statement(product_id=product_id, search=search, status=status)
        count_statement = select(func.count()).select_from(statement.subquery())

        missions_result = await self._session.execute(
            statement.order_by(Mission.created_at.desc()).offset(offset).limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(missions_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(self, mission_id: UUID, product_id: UUID | None = None) -> Mission | None:
        filters = [Mission.id == mission_id, Mission.deleted_at.is_(None)]
        if product_id is not None:
            filters.append(Mission.product_id == product_id)

        statement = select(Mission).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, product_id: UUID) -> Mission | None:
        """Used by MissionService to enforce the unique(name, product_id) rule."""
        statement = select(Mission).where(
            Mission.product_id == product_id,
            Mission.name == name,
            Mission.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, mission: Mission) -> Mission:
        await self._session.flush()
        await self._session.refresh(mission)
        return mission

    async def soft_delete(self, mission: Mission) -> Mission:
        await self._session.flush()
        await self._session.refresh(mission)
        return mission

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        product_id: UUID,
        search: str | None,
        status: MissionStatus | None,
    ) -> Select[tuple[Mission]]:
        statement = select(Mission).where(
            Mission.product_id == product_id,
            Mission.deleted_at.is_(None),
        )

        if status is not None:
            statement = statement.where(Mission.status == status)

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Mission.name.ilike(query),
                    Mission.description.ilike(query),
                    Mission.objective.ilike(query),
                )
            )

        return statement
