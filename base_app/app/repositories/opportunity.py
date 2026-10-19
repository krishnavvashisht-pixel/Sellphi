from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import Opportunity
from app.schemas.opportunity import OpportunityCreate, OpportunityUpdate


class OpportunityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, opportunity_id: UUID) -> Opportunity | None:
        stmt = select(Opportunity).where(Opportunity.id == opportunity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: UUID) -> list[Opportunity]:
        stmt = (
            select(Opportunity)
            .where(Opportunity.workspace_id == workspace_id)
            .order_by(Opportunity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, payload: OpportunityCreate) -> Opportunity:
        # Check if already saved by link/workspace to avoid duplicate records
        stmt = select(Opportunity).where(
            Opportunity.workspace_id == payload.workspace_id,
            Opportunity.article_link == payload.article_link,
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            # Update fields if new pitch was generated
            if payload.subject_line:
                existing.target_persona = payload.target_persona or existing.target_persona
                existing.subject_line = payload.subject_line
                existing.email_body = payload.email_body
                existing.follow_up_email = payload.follow_up_email
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        opp = Opportunity(
            workspace_id=payload.workspace_id,
            company_name=payload.company_name,
            company_domain=payload.company_domain,
            title=payload.title,
            article_link=payload.article_link,
            score=payload.score,
            evidence=payload.evidence,
            sales_implication=payload.sales_implication,
            target_persona=payload.target_persona,
            subject_line=payload.subject_line,
            email_body=payload.email_body,
            follow_up_email=payload.follow_up_email,
            status=payload.status,
            notes=payload.notes,
        )
        self.session.add(opp)
        await self.session.commit()
        await self.session.refresh(opp)
        return opp

    async def update(self, opportunity: Opportunity, payload: OpportunityUpdate) -> Opportunity:
        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(opportunity, key, val)
        await self.session.commit()
        await self.session.refresh(opportunity)
        return opportunity

    async def delete(self, opportunity: Opportunity) -> None:
        await self.session.delete(opportunity)
        await self.session.commit()
