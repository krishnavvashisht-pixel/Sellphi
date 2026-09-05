import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.database import Base
class PipelineState(str, Enum): PENDING="PENDING"; ENRICHING_COMPANY="ENRICHING_COMPANY"; EXECUTING_RESEARCH="EXECUTING_RESEARCH"; GATHERING_SIGNALS="GATHERING_SIGNALS"; UPDATING_MEMORY="UPDATING_MEMORY"; COMPLETED="COMPLETED"; FAILED="FAILED"
class PipelineExecution(Base):
    __tablename__ = "pipeline_executions"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    discovery_job_id = Column(PGUUID(as_uuid=True), ForeignKey("discovery_jobs.id"), nullable=True)
    state = Column(SQLEnum(PipelineState), nullable=False, default=PipelineState.PENDING)
    completed_stages = Column(JSONB, nullable=False, default=list); metrics = Column(JSONB, nullable=False, default=dict); logs = Column(JSONB, nullable=False, default=list)
    retry_count = Column(Integer, nullable=False, default=0); error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True); completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow); updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow); deleted_at = Column(DateTime, nullable=True)
    __table_args__ = (CheckConstraint('retry_count >= 0', name='chk_pipeline_retry_limit_positive'),)
