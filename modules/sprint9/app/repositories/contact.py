from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_persona import SeniorityLevel
from app.models.contact import Contact, ContactStatus, PreferredChannel, RelationshipStatus


class ContactRepository:
    """
    Pure data-access layer: CRUD, lookup by email/LinkedIn, search
    (name/title), company filtering, pagination, and soft delete only. No
    business rules live here — see ContactService for normalization,
    duplicate prevention, and cross-module validation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, contact: Contact) -> Contact:
        self._session.add(contact)
        await self._session.flush()
        await self._session.refresh(contact)
        return contact

    async def list(
        self,
        *,
        company_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        department: str | None = None,
        seniority: SeniorityLevel | None = None,
        relationship_status: RelationshipStatus | None = None,
        preferred_channel: PreferredChannel | None = None,
        status: ContactStatus | None = None,
    ) -> tuple[list[Contact], int]:
        statement = self._base_list_statement(
            company_id=company_id,
            search=search,
            department=department,
            seniority=seniority,
            relationship_status=relationship_status,
            preferred_channel=preferred_channel,
            status=status,
        )
        count_statement = select(func.count()).select_from(statement.subquery())

        contacts_result = await self._session.execute(
            statement.order_by(Contact.created_at.desc()).offset(offset).limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(contacts_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(self, contact_id: UUID, company_id: UUID | None = None) -> Contact | None:
        filters = [Contact.id == contact_id, Contact.deleted_at.is_(None)]
        if company_id is not None:
            filters.append(Contact.company_id == company_id)

        statement = select(Contact).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str, company_id: UUID) -> Contact | None:
        """Used by ContactService to enforce unique(email, company_id)."""
        statement = select(Contact).where(
            Contact.company_id == company_id,
            Contact.email == email,
            Contact.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def find_by_linkedin(self, linkedin_url: str, company_id: UUID) -> Contact | None:
        """Used by ContactService's duplicate-prevention check."""
        statement = select(Contact).where(
            Contact.company_id == company_id,
            Contact.linkedin_url == linkedin_url,
            Contact.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, contact: Contact) -> Contact:
        await self._session.flush()
        await self._session.refresh(contact)
        return contact

    async def soft_delete(self, contact: Contact) -> Contact:
        await self._session.flush()
        await self._session.refresh(contact)
        return contact

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        company_id: UUID,
        search: str | None,
        department: str | None,
        seniority: SeniorityLevel | None,
        relationship_status: RelationshipStatus | None,
        preferred_channel: PreferredChannel | None,
        status: ContactStatus | None,
    ) -> Select[tuple[Contact]]:
        statement = select(Contact).where(
            Contact.company_id == company_id,
            Contact.deleted_at.is_(None),
        )

        if status is not None:
            statement = statement.where(Contact.status == status)

        if department is not None:
            statement = statement.where(Contact.department == department)

        if seniority is not None:
            statement = statement.where(Contact.seniority == seniority)

        if relationship_status is not None:
            statement = statement.where(Contact.relationship_status == relationship_status)

        if preferred_channel is not None:
            statement = statement.where(Contact.preferred_channel == preferred_channel)

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Contact.full_name.ilike(query),
                    Contact.first_name.ilike(query),
                    Contact.last_name.ilike(query),
                    Contact.job_title.ilike(query),
                )
            )

        return statement
