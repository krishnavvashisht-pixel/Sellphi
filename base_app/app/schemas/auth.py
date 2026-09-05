from typing import Any

from pydantic import BaseModel, ConfigDict


class TokenPayload(BaseModel):
    subject: str
    issuer: str | None = None
    expires_at: int | None = None
    issued_at: int | None = None
    claims: dict[str, Any]

    model_config = ConfigDict(extra="allow")


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
