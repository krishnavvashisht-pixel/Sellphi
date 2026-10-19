from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, company: Company) -> Company:
        self._session.add(company)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def get_by_id(self, company_id: UUID) -> Company | None:
        statement = select(Company).where(Company.id == company_id, Company.deleted_at.is_(None))
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Company | None:
        """Case-insensitive exact match — the lookup half of the
        find-or-create stub pattern used by signal detection.

        Not a fuzzy/dedup match (no attempt to catch "Acme Inc." vs "Acme
        Incorporated" as the same company) — that's a real limitation
        worth knowing about, and one prospect discovery's vendor lookup
        (matching on domain, which is far more reliable) can improve on
        later rather than guessing a fuzzy-matching strategy now.
        """
        statement = select(Company).where(
            func.lower(Company.name) == name.lower(),
            Company.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        await self._session.commit()
