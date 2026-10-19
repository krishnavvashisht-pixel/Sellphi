from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mission import Mission


class MissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, mission: Mission) -> Mission:
        self._session.add(mission)
        await self._session.flush()
        await self._session.refresh(mission)
        return mission

    async def get_by_id(self, mission_id: UUID) -> Mission | None:
        statement = select(Mission).where(Mission.id == mission_id, Mission.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self._session.commit()
