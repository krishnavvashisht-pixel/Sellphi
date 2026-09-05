import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Enum, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base
from app.models.enums.opportunity import OpportunityStatus, OpportunityPriority

class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[OpportunityStatus] = mapped_column(Enum(OpportunityStatus), default=OpportunityStatus.NEW, nullable=False)
    probability_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasoning: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
