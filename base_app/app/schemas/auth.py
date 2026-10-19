from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    """What an admin can change about another (or their own) account.

    Both fields optional so a request only touches what it explicitly sets.
    """

    is_active: bool | None = None
    is_admin: bool | None = None
