from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.buyer_persona import BuyerPersona, BuyingRole, PersonaStatus, SeniorityLevel


class BuyerPersonaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, persona: BuyerPersona) -> BuyerPersona:
        self._session.add(persona)
        await self._session.flush()
        await self._session.refresh(persona)
        return persona

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: PersonaStatus | None = None,
        seniority: SeniorityLevel | None = None,
        buying_role: BuyingRole | None = None,
    ) -> tuple[list[BuyerPersona], int]:
        statement = self._base_list_statement(
            product_id=product_id,
            search=search,
            status=status,
            seniority=seniority,
            buying_role=buying_role,
        )
        count_statement = select(func.count()).select_from(statement.subquery())

        personas_result = await self._session.execute(
            statement.order_by(BuyerPersona.is_default.desc(), BuyerPersona.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_result = await self._session.execute(count_statement)

        return list(personas_result.scalars().all()), count_result.scalar_one()

    async def get_by_id(
        self, persona_id: UUID, product_id: UUID | None = None
    ) -> BuyerPersona | None:
        filters = [BuyerPersona.id == persona_id, BuyerPersona.deleted_at.is_(None)]
        if product_id is not None:
            filters.append(BuyerPersona.product_id == product_id)

        statement = select(BuyerPersona).where(*filters)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, product_id: UUID) -> BuyerPersona | None:
        """Used to enforce the unique(name, product_id) business rule pre-insert."""
        statement = select(BuyerPersona).where(
            BuyerPersona.product_id == product_id,
            BuyerPersona.name == name,
            BuyerPersona.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_default_for_product(self, product_id: UUID) -> BuyerPersona | None:
        statement = select(BuyerPersona).where(
            BuyerPersona.product_id == product_id,
            BuyerPersona.is_default.is_(True),
            BuyerPersona.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_defaults_for_product(self, product_id: UUID) -> list[BuyerPersona]:
        """Returns all non-deleted default personas for a product (used to enforce uniqueness)."""
        statement = select(BuyerPersona).where(
            BuyerPersona.product_id == product_id,
            BuyerPersona.is_default.is_(True),
            BuyerPersona.deleted_at.is_(None),
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def update(self, persona: BuyerPersona) -> BuyerPersona:
        await self._session.flush()
        await self._session.refresh(persona)
        return persona

    async def soft_delete(self, persona: BuyerPersona) -> BuyerPersona:
        await self._session.flush()
        await self._session.refresh(persona)
        return persona

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def _base_list_statement(
        self,
        *,
        product_id: UUID,
        search: str | None,
        status: PersonaStatus | None,
        seniority: SeniorityLevel | None,
        buying_role: BuyingRole | None,
    ) -> Select[tuple[BuyerPersona]]:
        statement = select(BuyerPersona).where(
            BuyerPersona.product_id == product_id,
            BuyerPersona.deleted_at.is_(None),
        )

        if status is not None:
            statement = statement.where(BuyerPersona.status == status)

        if seniority is not None:
            statement = statement.where(BuyerPersona.seniority == seniority)

        if buying_role is not None:
            statement = statement.where(BuyerPersona.buying_role == buying_role)

        if search:
            query = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    BuyerPersona.name.ilike(query),
                    BuyerPersona.job_title.ilike(query),
                )
            )

        return statement
