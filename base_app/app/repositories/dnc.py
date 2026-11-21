from uuid import UUID
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dnc import DncEntry


class DncRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entry: DncEntry) -> DncEntry:
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def get_by_id(self, dnc_id: UUID) -> DncEntry | None:
        statement = select(DncEntry).where(DncEntry.id == dnc_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> DncEntry | None:
        clean_domain = domain.lower().strip().replace("https://", "").replace("http://", "").split("/")[0]
        statement = select(DncEntry).where(DncEntry.domain == clean_domain)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def is_domain_blocked(self, domain: str | None) -> bool:
        if not domain:
            return False
        clean_domain = domain.lower().strip().replace("https://", "").replace("http://", "").split("/")[0]
        statement = select(DncEntry).where(DncEntry.domain == clean_domain)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def list_all(self, limit: int = 200) -> list[DncEntry]:
        statement = select(DncEntry).order_by(desc(DncEntry.created_at)).limit(limit)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def delete(self, entry: DncEntry) -> None:
        await self._session.delete(entry)
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
