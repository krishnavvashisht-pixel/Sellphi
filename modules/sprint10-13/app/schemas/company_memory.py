from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.company_memory import MemoryType, MemorySource, MemorySourceType, MemoryStatus
class CompanyMemoryBase(BaseModel):
    company_id: UUID; contact_id: Optional[UUID] = None; mission_id: Optional[UUID] = None; memory_type: MemoryType; title: str; content: str; summary: str
    importance: int = Field(50, ge=0, le=100); confidence_score: int = Field(0, ge=0, le=100); source: MemorySource; source_reference: Optional[UUID] = None; source_type: MemorySourceType
    tags: List[str] = Field(default_factory=list); metadata_json: Dict[str, Any] = Field(default_factory=dict, alias="metadata"); expires_at: Optional[datetime] = None
    model_config = ConfigDict(populate_by_name=True)
class CompanyMemoryCreate(CompanyMemoryBase): pass
class CompanyMemoryUpdate(BaseModel):
    memory_type: Optional[MemoryType] = None; title: Optional[str] = None; content: Optional[str] = None; summary: Optional[str] = None
    importance: Optional[int] = Field(None, ge=0, le=100); confidence_score: Optional[int] = Field(None, ge=0, le=100); status: Optional[MemoryStatus] = None
    model_config = ConfigDict(populate_by_name=True)
class CompanyMemoryResponse(CompanyMemoryBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID; ai_score: int; status: MemoryStatus; last_accessed_at: datetime; created_by: UUID; created_at: datetime; updated_at: datetime
class CompanyMemoryListResponse(BaseModel): items: List[CompanyMemoryResponse]; total: int; page: int; size: int
