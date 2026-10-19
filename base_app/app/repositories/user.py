from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        statement = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def list_all(self) -> list[User]:
        statement = select(User).where(User.deleted_at.is_(None)).order_by(User.created_at)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def count_admins(self) -> int:
        statement = (
            select(func.count())
            .select_from(User)
            .where(User.deleted_at.is_(None), User.is_admin.is_(True))
        )
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
