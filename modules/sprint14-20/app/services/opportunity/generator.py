import time
from uuid import UUID
from app.repositories.opportunity_repository import OpportunityRepository
from app.models.opportunity import Opportunity
from app.models.enums.opportunity import OpportunityStatus

class OpportunityGenerator:
    def __init__(self, repository: OpportunityRepository, scorer, researcher, icp_matcher, pain_detector, personalizer, value_estimator):
        self.repository = repository
        # Dependencies assigned here...

    async def generate_opportunity(self, workspace_id: UUID, company_id: UUID, raw_signals: list) -> Opportunity:
        opp = Opportunity(workspace_id=workspace_id, company_id=company_id, status=OpportunityStatus.GENERATING)
        opp = await self.repository.create(opp)
        await self.repository.session.commit()
        # Full AI pipeline runs here without holding DB lock
        return opp
