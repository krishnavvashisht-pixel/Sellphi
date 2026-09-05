import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.enums import SignalType, SignalCategory, SourceType, ProcessingStatus, SignalStatus

class BuyingSignal(Base):
    __tablename__ = "buying_signals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True)
    signal_type = Column(SQLEnum(SignalType), nullable=False)
    category = Column(SQLEnum(SignalCategory), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    source_name = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    confidence_score = Column(Integer, nullable=False, default=0)
    impact_score = Column(Integer, nullable=False, default=0)
    urgency_score = Column(Integer, nullable=False, default=0)
    freshness_score = Column(Integer, nullable=False, default=0)
    ai_score = Column(Integer, nullable=False, default=0)
    evidence = Column(JSONB, nullable=False, default=dict)
    metadata = Column(JSONB, nullable=False, default=dict)
    raw_payload = Column(JSONB, nullable=True)
    embedding_id = Column(UUID(as_uuid=True), nullable=True)
    llm_summary = Column(Text, nullable=True)
    reasoning = Column(JSONB, nullable=True)
    processing_status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.PENDING)
    status = Column(SQLEnum(SignalStatus), nullable=False, default=SignalStatus.ACTIVE)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint('company_id', 'signal_type', 'source_url', 'published_at', name='uq_signals_dup_check'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 100', name='chk_confidence_score_range'),
        CheckConstraint('impact_score >= 0 AND impact_score <= 100', name='chk_impact_score_range'),
        CheckConstraint('urgency_score >= 0 AND urgency_score <= 100', name='chk_urgency_score_range'),
        CheckConstraint('freshness_score >= 0 AND freshness_score <= 100', name='chk_freshness_score_range'),
        CheckConstraint('ai_score >= 0 AND ai_score <= 100', name='chk_ai_score_range'),
        Index('idx_buying_signals_company_status', 'company_id', 'status'),
        Index('idx_buying_signals_mission', 'mission_id'),
        Index('idx_buying_signals_lookup_filters', 'category', 'signal_type', 'processing_status'),
    )
