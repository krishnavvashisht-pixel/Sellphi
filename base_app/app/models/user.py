from enum import StrEnum
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    SDR = "sdr"
    VIEWER = "viewer"


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A person who can log in to Sellphi.

    Role-based access control (RBAC):
    - super_admin: System owner, manages team roles, can promote/demote admins, audits logs.
    - admin: Manages team members and workspace operations. Cannot demote super_admin.
    - sdr: Standard sales rep (scans buying signals, drafts 4-step cadences, saves leads).
    - viewer: Read-only analyst.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.SDR.value, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_recovery_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __init__(self, **kwargs) -> None:
        if "role" not in kwargs or kwargs["role"] is None:
            kwargs["role"] = UserRole.ADMIN.value if kwargs.get("is_admin") else UserRole.SDR.value
        if "mfa_enabled" not in kwargs or kwargs["mfa_enabled"] is None:
            kwargs["mfa_enabled"] = False
        super().__init__(**kwargs)
