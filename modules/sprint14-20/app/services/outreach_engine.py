import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta
from app.repositories.outreach_campaign_repository import OutreachCampaignRepository
from app.models.outreach_campaign import OutreachCampaign
from app.models.enums.outreach import CampaignStatus

class OutreachEngine:
    def __init__(self, repository: OutreachCampaignRepository, event_bus):
        self.repository = repository
        self.event_bus = event_bus

    async def create_campaign(self, cmd) -> OutreachCampaign:
        async with self.repository.session.begin():
            campaign = OutreachCampaign(workspace_id=cmd.workspace_id, company_id=cmd.company_id, name=cmd.name, type=cmd.type)
            await self.repository.create_campaign(campaign)
        return campaign
