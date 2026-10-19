from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_search import SavedSearch
from app.schemas.saved_search import SavedSearchCreate


class SavedSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, search_id: UUID) -> SavedSearch | None:
        stmt = select(SavedSearch).where(SavedSearch.id == search_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: UUID) -> list[SavedSearch]:
        stmt = (
            select(SavedSearch)
            .where(SavedSearch.workspace_id == workspace_id)
            .order_by(SavedSearch.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, payload: SavedSearchCreate) -> SavedSearch:
        search = SavedSearch(
            workspace_id=payload.workspace_id,
            name=payload.name,
            query=payload.query,
            region=payload.region,
            limit=payload.limit,
        )
        self.session.add(search)
        await self.session.commit()
        await self.session.refresh(search)
        return search

    async def delete(self, saved_search: SavedSearch) -> None:
        await self.session.delete(saved_search)
        await self.session.commit()
