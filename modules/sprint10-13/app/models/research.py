import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
class ResearchType(str, Enum):
    COMPANY_PROFILE="COMPANY_PROFILE"; CONTACT_PROFILE="CONTACT_PROFILE"; COMPETITOR_ANALYSIS="COMPETITOR_ANALYSIS"
    INDUSTRY_ANALYSIS="INDUSTRY_ANALYSIS"; TECH_STACK_ANALYSIS="TECH_STACK_ANALYSIS"; BUYING_INTENT_ANALYSIS="BUYING_INTENT_ANALYSIS"; CUSTOM="CUSTOM"
class ResearchSource(str, Enum): AI_AGENT="AI_AGENT"; MANUAL="MANUAL"; LINKEDIN="LINKEDIN"; CRUNCHBASE="CRUNCHBASE"; CLEARBIT="CLEARBIT"; G2="G2"; WEBSITE="WEBSITE"; APOLLO="APOLLO"; ZOOMINFO="ZOOMINFO"; PERPLEXITY="PERPLEXITY"; OPENAI="OPENAI"
class ResearchProcessingStatus(str, Enum): PENDING="PENDING"; PROCESSING="PROCESSING"; COMPLETED="COMPLETED"; FAILED="FAILED"
class ResearchStatus(str, Enum): ACTIVE="ACTIVE"; ARCHIVED="ARCHIVED"; SUPERSEDED="SUPERSEDED"
class VectorStatus(str, Enum): PENDING="PENDING"; INDEXED="INDEXED"; FAILED="FAILED"
class Research(Base):
    __tablename__ = "research"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True)
    title = Column(Text, nullable=False); research_type = Column(SQLEnum(ResearchType), nullable=False)
    source = Column(SQLEnum(ResearchSource), nullable=False); summary = Column(Text, nullable=False)
    company_overview = Column(Text, nullable=True); business_model = Column(Text, nullable=True)
    industry = Column(String(255), nullable=True); employee_count = Column(Integer, nullable=True)
    revenue_range = Column(String(100), nullable=True); headquarters = Column(String(255), nullable=True); website = Column(Text, nullable=True)
    technologies = Column(JSONB, nullable=False, default=list); competitors = Column(JSONB, nullable=False, default=list)
    pain_points = Column(JSONB, nullable=False, default=list); opportunities = Column(JSONB, nullable=False, default=list)
    evidence = Column(JSONB, nullable=False, default=dict); citations = Column(JSONB, nullable=False, default=list); llm_summary = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=False, default=0); completeness_score = Column(Integer, nullable=False, default=0)
    freshness_score = Column(Integer, nullable=False, default=0); ai_score = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)
    processing_status = Column(SQLEnum(ResearchProcessingStatus), nullable=False, default=ResearchProcessingStatus.PENDING)
    status = Column(SQLEnum(ResearchStatus), nullable=False, default=ResearchStatus.ACTIVE)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)
    embedding_id = Column(UUID(as_uuid=True), nullable=True); raw_payload = Column(JSONB, nullable=True); reasoning = Column(JSONB, nullable=True); vector_status = Column(SQLEnum(VectorStatus), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False); created_at = Column(DateTime, nullable=False, default=datetime.utcnow); updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow); deleted_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint('company_id', 'contact_id', 'mission_id', 'research_type', 'version', name='uq_research_version_control'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='chk_res_confidence_score_range'),
        CheckConstraint('completeness_score >= 0 AND completeness_score <= 100', name='chk_res_completeness_score_range'),
        CheckConstraint('freshness_score >= 0 AND freshness_score <= 100', name='chk_res_freshness_score_range'),
        CheckConstraint('ai_score >= 0 AND ai_score <= 100', name='chk_res_ai_score_range'),
        Index('idx_research_lookup_company_status', 'company_id', 'status'),
        Index('idx_research_lookup_contact', 'contact_id'),
        Index('idx_research_lookup_mission', 'mission_id'),
        Index('idx_research_lookup_filters', 'research_type', 'processing_status'),
    )
