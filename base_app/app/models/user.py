from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A person who can log in to Sellphi.

    Anyone can sign up (public registration) — the first person to ever
    sign up is automatically made an admin (is_admin=True); everyone after
    that signs up as a regular, non-admin user. Admins can promote/demote
    or deactivate other users; see services/auth.py.

    No workspace_id yet: the build plan's MVP scope collapses multi-tenancy
    (Section 5, "one Workspace ... skip multi-tenancy and RBAC entirely").
    Multiple *users* now exist, but they all still share the one workspace.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
