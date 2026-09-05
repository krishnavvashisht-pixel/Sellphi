from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import SignalType, SignalCategory, SourceType, ProcessingStatus, SignalStatus

class BuyingSignalBase(BaseModel):
    company_id: UUID; mission_id: Optional[UUID] = None; signal_type: SignalType; category: SignalCategory
    title: str; description: str; summary: str; source_name: str; source_url: str; source_type: SourceType
    published_at: datetime; expires_at: Optional[datetime] = None
    confidence_score: int = Field(0, ge=0, le=100); impact_score: int = Field(0, ge=0, le=100); urgency_score: int = Field(0, ge=0, le=100)
    evidence: Dict[str, Any] = Field(default_factory=dict); metadata: Dict[str, Any] = Field(default_factory=dict); raw_payload: Optional[Dict[str, Any]] = None
class BuyingSignalCreate(BuyingSignalBase): pass
class BuyingSignalUpdate(BaseModel):
    mission_id: Optional[UUID] = None; signal_type: Optional[SignalType] = None; category: Optional[SignalCategory] = None
    title: Optional[str] = None; description: Optional[str] = None; summary: Optional[str] = None
    source_name: Optional[str] = None; source_url: Optional[str] = None; source_type: Optional[SourceType] = None
    published_at: Optional[datetime] = None; expires_at: Optional[datetime] = None
    confidence_score: Optional[int] = Field(None, ge=0, le=100); impact_score: Optional[int] = Field(None, ge=0, le=100); urgency_score: Optional[int] = Field(None, ge=0, le=100)
    evidence: Optional[Dict[str, Any]] = None; metadata: Optional[Dict[str, Any]] = None; status: Optional[SignalStatus] = None
class BuyingSignalResponse(BuyingSignalBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID; detected_at: datetime; freshness_score: int; ai_score: int; embedding_id: Optional[UUID] = None
    llm_summary: Optional[str] = None; reasoning: Optional[Dict[str, Any]] = None; processing_status: ProcessingStatus
    status: SignalStatus; is_verified: bool; created_by: UUID; created_at: datetime; updated_at: datetime
class BuyingSignalListResponse(BaseModel):
    items: List[BuyingSignalResponse]; total: int; page: int; size: int
