from datetime import datetime
from typing import Any, List, Optional, Tuple, UUID
from app.models.company_memory import CompanyMemory, MemoryType, MemoryStatus
from app.schemas.company_memory import CompanyMemoryCreate, CompanyMemoryUpdate
from app.repositories.company_memory import CompanyMemoryRepository
class CompanyMemoryService:
    def __init__(self, repository: CompanyMemoryRepository, company_repo: Any): self.repository = repository; self.company_repo = company_repo
    def _calculate_ai_score(self, confidence: int, importance: int) -> int: return int((confidence * 0.4) + (importance * 0.6))
    def get_memory(self, memory_id: UUID, current_user_id: UUID) -> CompanyMemory:
        entity = self.repository.get_by_id(memory_id)
        if entity: entity.last_accessed_at = datetime.utcnow(); self.repository.update(entity)
        return entity
    def create_memory(self, schema: CompanyMemoryCreate, current_user_id: UUID) -> CompanyMemory:
        ai_score = self._calculate_ai_score(schema.confidence_score, schema.importance)
        db_memory = CompanyMemory(**schema.model_dump(by_alias=False), ai_score=ai_score, status=MemoryStatus.ACTIVE, last_accessed_at=datetime.utcnow(), created_by=current_user_id)
        return self.repository.create(db_memory)
    def update_memory(self, memory_id: UUID, schema: CompanyMemoryUpdate) -> CompanyMemory:
        entity = self.repository.get_by_id(memory_id)
        update_data = schema.model_dump(exclude_unset=True, by_alias=False)
        for key, value in update_data.items(): setattr(entity, key, value)
        if any(k in update_data for k in ["confidence_score", "importance"]): entity.ai_score = self._calculate_ai_score(entity.confidence_score, entity.importance)
        self.repository.update(entity)
        return entity
