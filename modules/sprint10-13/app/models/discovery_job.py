import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, Enum as SQLEnum, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.database import Base
class JobStatus(str, Enum): PENDING="PENDING"; RUNNING="RUNNING"; COMPLETED="COMPLETED"; FAILED="FAILED"; CANCELLED="CANCELLED"
class DiscoveryProvider(str, Enum): LINKEDIN="LINKEDIN"; CRUNCHBASE="CRUNCHBASE"; APOLLO="APOLLO"; ZOOMINFO="ZOOMINFO"; CUSTOM="CUSTOM"; MOCK="MOCK"
class DiscoveryStage(str, Enum): INITIALIZATION="INITIALIZATION"; EXTRACTION="EXTRACTION"; ENRICHMENT="ENRICHMENT"; FILTERING="FILTERING"; SAVING="SAVING"; FINALIZATION="FINALIZATION"
class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(PGUUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    mission_id = Column(PGUUID(as_uuid=True), ForeignKey("missions.id"), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    provider = Column(SQLEnum(DiscoveryProvider), nullable=False)
    current_stage = Column(SQLEnum(DiscoveryStage), nullable=False, default=DiscoveryStage.INITIALIZATION)
    configuration = Column(JSONB, nullable=False, default=dict)
    total_discovered = Column(Integer, nullable=False, default=0); total_processed = Column(Integer, nullable=False, default=0)
    total_saved = Column(Integer, nullable=False, default=0); total_duplicates = Column(Integer, nullable=False, default=0); total_failed = Column(Integer, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0); error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True); completed_at = Column(DateTime, nullable=True)
    created_by = Column(PGUUID(as_uuid=True), nullable=False); created_at = Column(DateTime, nullable=False, default=datetime.utcnow); updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow); deleted_at = Column(DateTime, nullable=True)
    __table_args__ = (
        CheckConstraint('retry_count >= 0 AND retry_count <= 3', name='chk_discovery_retry_limit'),
        CheckConstraint('total_discovered >= 0', name='chk_discovery_totals_positive'),
        Index('idx_unique_running_job_per_mission', 'mission_id', unique=True, postgresql_where=text("status = 'RUNNING'")),
    )
