from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.company_memory import CompanyMemory, MemoryType, MemoryStatus
from app.repositories.base import BaseRepository
class CompanyMemoryRepository(BaseRepository[CompanyMemory]):
    def __init__(self, db: Session): super().__init__(model=CompanyMemory, db=db)
    def get_by_id(self, memory_id: UUID) -> Optional[CompanyMemory]: return self.db.query(CompanyMemory).filter(CompanyMemory.id == memory_id, CompanyMemory.deleted_at.is_(None)).first()
    def get_duplicate(self, company_id: UUID, memory_type: MemoryType, title: str) -> Optional[CompanyMemory]: return self.db.query(CompanyMemory).filter(CompanyMemory.company_id == company_id, CompanyMemory.memory_type == memory_type, CompanyMemory.title == title, CompanyMemory.deleted_at.is_(None)).first()
    def search_memories(self, company_id=None, tags=None, search_term=None, page=1, size=20):
        query = self.db.query(CompanyMemory).filter(CompanyMemory.deleted_at.is_(None))
        if company_id: query = query.filter(CompanyMemory.company_id == company_id)
        if tags: query = query.filter(CompanyMemory.tags.contains(tags))
        if search_term: query = query.filter(or_(CompanyMemory.title.ilike(f"%{search_term}%"), CompanyMemory.content.ilike(f"%{search_term}%")))
        total = query.count()
        items = query.order_by(CompanyMemory.last_accessed_at.desc(), CompanyMemory.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total
