from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class TokenPayload(BaseModel):
    subject: str
    issuer: str | None = None
    expires_at: int | None = None
    issued_at: int | None = None
    claims: dict[str, Any]

    model_config = ConfigDict(extra="allow")


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserPublic(BaseModel):
    """A user record safe to show back over the API — never the password hash."""

    id: UUID
    email: EmailStr
    is_active: bool
    is_admin: bool
    role: str = "sdr"
    mfa_enabled: bool = False
    created_at: datetime

    @field_validator("role", mode="before")
    @classmethod
    def default_role(cls, v: Any) -> str:
        return v or "sdr"

    @field_validator("mfa_enabled", mode="before")
    @classmethod
    def default_mfa(cls, v: Any) -> bool:
        return bool(v)

    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    """What an admin can change about another (or their own) account.

    Fields are optional so a request only touches what it explicitly sets.
    """

    is_active: bool | None = None
    is_admin: bool | None = None
    role: str | None = None


class CreateInvitationRequest(BaseModel):
    invited_email: EmailStr
    role: str = Field(default="admin", pattern="^(super_admin|admin|sdr|viewer)$")


class AcceptInvitationRequest(BaseModel):
    token: str = Field(min_length=8)
    password: str = Field(min_length=8)


class InvitationPublic(BaseModel):
    id: UUID
    inviter_email: str
    invited_email: EmailStr
    role: str
    token: str
    expires_at: datetime
    accepted_at: datetime | None = None
    is_revoked: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogPublic(BaseModel):
    id: UUID
    actor_email: str
    action: str
    target_email: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    details: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MfaSetupResponse(BaseModel):
    secret: str
    backup_code: str
    instructions: str


class MfaVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)
