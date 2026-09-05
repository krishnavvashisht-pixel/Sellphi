import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base
class MemoryType(str, Enum): FACT="FACT"; PREFERENCE="PREFERENCE"; HISTORICAL_CONTEXT="HISTORICAL_CONTEXT"; STRATEGIC_INITIATIVE="STRATEGIC_INITIATIVE"; OBJECTION="OBJECTION"; RELATIONSHIP_DYNAMICS="RELATIONSHIP_DYNAMICS"; CUSTOM="CUSTOM"
class MemorySource(str, Enum): SYSTEM="SYSTEM"; USER="USER"; AI_AGENT="AI_AGENT"; INTEGRATION="INTEGRATION"; WEB_SCRAPER="WEB_SCRAPER"; THIRD_PARTY_API="THIRD_PARTY_API"; UPLOAD="UPLOAD"
class MemorySourceType(str, Enum): RESEARCH="RESEARCH"; BUYING_SIGNAL="BUYING_SIGNAL"; EMAIL="EMAIL"; CALL_TRANSCRIPT="CALL_TRANSCRIPT"; MANUAL_ENTRY="MANUAL_ENTRY"; OTHER="OTHER"
class MemoryStatus(str, Enum): ACTIVE="ACTIVE"; ARCHIVED="ARCHIVED"; EXPIRED="EXPIRED"
class CompanyMemory(Base):
    __tablename__ = "company_memories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True)
    memory_type = Column(SQLEnum(MemoryType), nullable=False)
    title = Column(Text, nullable=False); content = Column(Text, nullable=False); summary = Column(Text, nullable=False)
    importance = Column(Integer, nullable=False, default=50); confidence_score = Column(Integer, nullable=False, default=0); ai_score = Column(Integer, nullable=False, default=0)
    source = Column(SQLEnum(MemorySource), nullable=False); source_reference = Column(UUID(as_uuid=True), nullable=True); source_type = Column(SQLEnum(MemorySourceType), nullable=False)
    tags = Column(JSONB, nullable=False, default=list); metadata_json = Column("metadata", JSONB, nullable=False, default=dict); reasoning = Column(JSONB, nullable=True)
    status = Column(SQLEnum(MemoryStatus), nullable=False, default=MemoryStatus.ACTIVE); expires_at = Column(DateTime, nullable=True); last_accessed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=False); created_at = Column(DateTime, nullable=False, default=datetime.utcnow); updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow); deleted_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint('company_id', 'memory_type', 'title', name='uq_company_memory_strategy'),
        CheckConstraint('importance >= 0 AND importance <= 100', name='chk_mem_importance_range'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='chk_mem_confidence_score_range'),
        CheckConstraint('ai_score >= 0 AND ai_score <= 100', name='chk_mem_ai_score_range')
    )
