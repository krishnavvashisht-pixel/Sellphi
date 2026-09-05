from datetime import datetime
from typing import Any, List, Optional, Tuple, UUID
from app.models.research import Research, ResearchType, ResearchStatus, ResearchProcessingStatus
from app.schemas.research import ResearchCreate, ResearchUpdate
from app.repositories.research import ResearchRepository
from app.events import event_bus
from app.events.research import ResearchCreated, ResearchUpdated, ResearchScored, ResearchDeleted
class ResearchService:
    def __init__(self, repository: ResearchRepository, company_repo: Any, contact_repo: Any, mission_repo: Any):
        self.repository = repository; self.company_repo = company_repo; self.contact_repo = contact_repo; self.mission_repo = mission_repo
    def _calculate_freshness_score(self, updated_at: datetime) -> int:
        days = (datetime.utcnow() - updated_at).total_seconds() / 86400
        return max(0, min(100, 100 - int(days * 2)))
    def _calculate_ai_score(self, confidence: int, completeness: int, freshness: int) -> int:
        return int((confidence * 0.4) + (completeness * 0.3) + (freshness * 0.3))
    def get_by_id(self, research_id: UUID) -> Optional[Research]: return self.repository.get_by_id(research_id)
    def search_research(self, **kwargs) -> Tuple[List[Research], int]: return self.repository.search_research(**kwargs)
    def get_latest_version(self, company_id: UUID, contact_id: Optional[UUID], research_type: ResearchType) -> Optional[Research]: return self.repository.get_latest_version(company_id, contact_id, research_type)
    def create_research(self, schema: ResearchCreate, current_user_id: UUID) -> Research:
        latest = self.repository.get_latest_version(schema.company_id, schema.contact_id, schema.research_type)
        version = (latest.version + 1) if latest else 1
        if latest and latest.status == ResearchStatus.ACTIVE:
            latest.status = ResearchStatus.SUPERSEDED
            self.repository.update(latest)
        freshness = 100
        ai_score = self._calculate_ai_score(schema.confidence_score, schema.completeness_score, freshness)
        db_research = Research(**schema.model_dump(by_alias=False), version=version, freshness_score=freshness, ai_score=ai_score, processing_status=ResearchProcessingStatus.COMPLETED, status=ResearchStatus.ACTIVE, created_by=current_user_id)
        created_entity = self.repository.create(db_research)
        event_bus.emit(ResearchCreated(research_id=created_entity.id, company_id=created_entity.company_id, version=version, created_by=current_user_id))
        return created_entity
    def update_research(self, research_id: UUID, schema: ResearchUpdate) -> Research:
        entity = self.repository.get_by_id(research_id)
        update_data = schema.model_dump(exclude_unset=True, by_alias=False)
        for key, value in update_data.items(): setattr(entity, key, value)
        entity.freshness_score = self._calculate_freshness_score(entity.updated_at)
        entity.ai_score = self._calculate_ai_score(entity.confidence_score, entity.completeness_score, entity.freshness_score)
        self.repository.update(entity)
        return entity
