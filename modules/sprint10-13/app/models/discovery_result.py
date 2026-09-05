import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.database import Base
class ResultStatus(str, Enum): SAVED="SAVED"; REJECTED="REJECTED"; DUPLICATE="DUPLICATE"; FAILED="FAILED"
class DiscoveryResult(Base):
    __tablename__ = "discovery_results"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey("discovery_jobs.id"), nullable=False)
    domain = Column(String(255), nullable=False); company_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(ResultStatus), nullable=False)
    score = Column(Integer, nullable=True); grade = Column(String(2), nullable=True)
    rejection_reasons = Column(JSONB, nullable=False, default=list)
    raw_payload = Column(JSONB, nullable=False, default=dict); enriched_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index('idx_discovery_results_domain_job', 'domain', 'job_id', unique=True),)
