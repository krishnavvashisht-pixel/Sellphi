import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Enum, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base
from app.models.enums.decision import DecisionStatus, ActionType

class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[ActionType] = mapped_column(Enum(ActionType), nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus), default=DecisionStatus.PROPOSED, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    is_autonomous: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
