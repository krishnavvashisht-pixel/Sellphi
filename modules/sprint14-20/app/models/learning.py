import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Enum, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.base import Base
from app.models.enums.learning import FeedbackType, ModelCategory

class FeedbackSignal(Base):
    __tablename__ = "feedback_signals"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType), nullable=False)
    is_positive: Mapped[bool] = mapped_column(Boolean, nullable=False)

class ModelWeight(Base):
    __tablename__ = "model_weights"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    category: Mapped[ModelCategory] = mapped_column(Enum(ModelCategory), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight_value: Mapped[float] = mapped_column(Float, nullable=False)
