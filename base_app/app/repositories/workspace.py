from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, workspace: Workspace) -> Workspace:
        self._session.add(workspace)
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[Workspace]:
        statement = (
            select(Workspace)
            .where(Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_by_owner(self, owner_id: UUID) -> list[Workspace]:
        statement = (
            select(Workspace)
            .where(Workspace.owner_id == owner_id, Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        statement = select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Workspace | None:
        statement = select(Workspace).where(
            Workspace.slug == slug,
            Workspace.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, workspace: Workspace) -> Workspace:
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def soft_delete(self, workspace: Workspace) -> Workspace:
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
