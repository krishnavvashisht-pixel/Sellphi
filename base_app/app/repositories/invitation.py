from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invitation import AdminInvitation


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, invitation: AdminInvitation) -> AdminInvitation:
        self._session.add(invitation)
        await self._session.flush()
        await self._session.refresh(invitation)
        return invitation

    async def get_by_token(self, token: str) -> AdminInvitation | None:
        statement = select(AdminInvitation).where(
            AdminInvitation.token == token,
            AdminInvitation.is_revoked.is_(False),
            AdminInvitation.accepted_at.is_(None),
        )
        result = await self._session.execute(statement)
        invitation = result.scalar_one_or_none()
        if invitation and invitation.expires_at < datetime.now(UTC):
            return None
        return invitation

    async def get_by_id(self, invitation_id: UUID) -> AdminInvitation | None:
        statement = select(AdminInvitation).where(AdminInvitation.id == invitation_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100) -> list[AdminInvitation]:
        statement = select(AdminInvitation).order_by(desc(AdminInvitation.created_at)).limit(limit)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def commit(self) -> None:
        await self._session.commit()
