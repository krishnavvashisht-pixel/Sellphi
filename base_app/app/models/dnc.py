from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DncEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Do-Not-Contact (DNC) domain blacklist.
    
    Prevents autonomous outreach to competitors, current customers, or opt-outs.
    """

    __tablename__ = "dnc_entries"

    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), default="Competitor", nullable=True)
    added_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
