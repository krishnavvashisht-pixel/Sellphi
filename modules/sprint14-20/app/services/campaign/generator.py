from uuid import UUID
from app.repositories.campaign_repository import CampaignRepository
from app.models.campaign import Campaign
from app.models.enums.campaign import CampaignStatus, CampaignObjective

class CampaignGenerator:
    def __init__(self, campaign_repo, opportunity_repo, email_gen, linkedin_gen, sequence_engine):
        self.campaign_repo = campaign_repo

    async def generate_campaign(self, workspace_id: UUID, opportunity_id: UUID) -> Campaign:
        async with self.campaign_repo.session.begin():
            campaign = Campaign(workspace_id=workspace_id, opportunity_id=opportunity_id, name="Outreach", status=CampaignStatus.GENERATING, objective=CampaignObjective.MEETING)
            campaign = await self.campaign_repo.create(campaign)
        return campaign
