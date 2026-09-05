from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.research import Research, ResearchType, ResearchStatus, ResearchProcessingStatus
from app.repositories.base import BaseRepository
class ResearchRepository(BaseRepository[Research]):
    def __init__(self, db: Session): super().__init__(model=Research, db=db)
    def get_by_id(self, research_id: UUID) -> Optional[Research]: return self.db.query(Research).filter(Research.id == research_id, Research.deleted_at.is_(None)).first()
    def get_latest_version(self, company_id: UUID, contact_id: Optional[UUID], research_type: ResearchType) -> Optional[Research]:
        return self.db.query(Research).filter(Research.company_id == company_id, Research.contact_id == contact_id, Research.research_type == research_type, Research.deleted_at.is_(None)).order_by(Research.version.desc()).first()
    def search_research(self, company_id=None, contact_id=None, mission_id=None, research_type=None, status=None, processing_status=None, search_term=None, page=1, size=20) -> Tuple[List[Research], int]:
        query = self.db.query(Research).filter(Research.deleted_at.is_(None))
        if company_id: query = query.filter(Research.company_id == company_id)
        if search_term: query = query.filter(or_(Research.title.ilike(f"%{search_term}%"), Research.summary.ilike(f"%{search_term}%")))
        total = query.count()
        items = query.order_by(Research.version.desc(), Research.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total
    def soft_delete(self, research_id: UUID) -> bool:
        entity = self.get_by_id(research_id)
        if entity: entity.deleted_at = datetime.utcnow(); self.db.commit(); return True
        return False
