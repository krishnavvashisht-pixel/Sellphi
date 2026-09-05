from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyStatus, FundingStage


class CompanyRepository:
    """
    Pure data-access layer: CRUD, search (name/domain/website/industry),
    pagination, workspace filtering, and soft delete only. No business rules
    live here — see CompanyService for normalization, uniqueness, and scoring.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, company: Company) -> Company:
        self._session.add(company)
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        industry: str | None = None,
        status: CompanyStatus | None = None,
        funding_stage: FundingStage | None = None,
        company_size: str | None = None,
        country: str | None = None,
        mission_id: UUID | None = None,
    ) -> tuple[list[Company], int]:
        statement = self._base_list_statement(
            workspace_id=workspace_id,
            search=search,
            industry=industry,
            status=status,
            funding_stage=funding_stage,
            company_size=company_size,
            country=country,
            mission_id=mission_id,
        )
        count_statement = select(func.count()).select_from(statement.subquery())

        companies_result = await self._session.execute(
            statement.order_by(Company.created_at.desc()).offset(offset).limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(companies_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(self, company_id: UUID, workspace_id: UUID | None = None) -> Company | None:
        filters = [Company.id == company_id, Company.deleted_at.is_(None)]
        if workspace_id is not None:
            filters.append(Company.workspace_id == workspace_id)

        statement = select(Company).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_domain(self, domain: str, workspace_id: UUID) -> Company | None:
        """Used by CompanyService to enforce the unique(domain, workspace_id) rule
        and by future enrichment workflows to find an existing company by domain."""
        statement = select(Company).where(
            Company.workspace_id == workspace_id,
            Company.domain == domain,
            Company.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, company: Company) -> Company:
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def soft_delete(self, company: Company) -> Company:
        await self._session.flush()
        await self._session.refresh(company)
        return company

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        workspace_id: UUID,
        search: str | None,
        industry: str | None,
        status: CompanyStatus | None,
        funding_stage: FundingStage | None,
        company_size: str | None,
        country: str | None,
        mission_id: UUID | None,
    ) -> Select[tuple[Company]]:
        statement = select(Company).where(
            Company.workspace_id == workspace_id,
            Company.deleted_at.is_(None),
        )

        if status is not None:
            statement = statement.where(Company.status == status)

        if industry is not None:
            statement = statement.where(Company.industry == industry)

        if funding_stage is not None:
            statement = statement.where(Company.funding_stage == funding_stage)

        if company_size is not None:
            statement = statement.where(Company.company_size == company_size)

        if country is not None:
            statement = statement.where(Company.headquarters_country == country)

        if mission_id is not None:
            statement = statement.where(Company.mission_id == mission_id)

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Company.name.ilike(query),
                    Company.domain.ilike(query),
                    Company.website.ilike(query),
                    Company.industry.ilike(query),
                )
            )

        return statement
