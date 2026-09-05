from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.research import ResearchType, ResearchSource, ResearchProcessingStatus, ResearchStatus, VectorStatus
class ResearchBase(BaseModel):
    company_id: UUID; contact_id: Optional[UUID] = None; mission_id: Optional[UUID] = None; title: str; research_type: ResearchType; source: ResearchSource; summary: str
    company_overview: Optional[str] = None; business_model: Optional[str] = None; industry: Optional[str] = None; employee_count: Optional[int] = None; revenue_range: Optional[str] = None; headquarters: Optional[str] = None; website: Optional[str] = None
    technologies: List[str] = Field(default_factory=list); competitors: List[str] = Field(default_factory=list); pain_points: List[str] = Field(default_factory=list); opportunities: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict); citations: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_score: int = Field(0, ge=0, le=100); completeness_score: int = Field(0, ge=0, le=100)
    metadata_json: Dict[str, Any] = Field(default_factory=dict, alias="metadata"); raw_payload: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(populate_by_name=True)
class ResearchCreate(ResearchBase): pass
class ResearchUpdate(BaseModel):
    title: Optional[str] = None; summary: Optional[str] = None; confidence_score: Optional[int] = Field(None, ge=0, le=100); completeness_score: Optional[int] = Field(None, ge=0, le=100); status: Optional[ResearchStatus] = None
    model_config = ConfigDict(populate_by_name=True)
class ResearchResponse(ResearchBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID; llm_summary: Optional[str] = None; freshness_score: int; ai_score: int; version: int; processing_status: ResearchProcessingStatus; status: ResearchStatus
    embedding_id: Optional[UUID] = None; reasoning: Optional[Dict[str, Any]] = None; vector_status: Optional[VectorStatus] = None; created_by: UUID; created_at: datetime; updated_at: datetime
class ResearchListResponse(BaseModel): items: List[ResearchResponse]; total: int; page: int; size: int
