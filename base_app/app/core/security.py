from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import Settings, get_settings
from app.schemas.auth import TokenPayload

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: str,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    now = datetime.now(UTC)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=resolved_settings.jwt_access_token_expire_minutes)
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "iss": resolved_settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        resolved_settings.jwt_secret_key.get_secret_value(),
        algorithm=resolved_settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings | None = None) -> TokenPayload | None:
    resolved_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            resolved_settings.jwt_secret_key.get_secret_value(),
            algorithms=[resolved_settings.jwt_algorithm],
            issuer=resolved_settings.jwt_issuer,
        )
    except InvalidTokenError:
        return None

    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None

    return TokenPayload(
        subject=subject,
        issuer=payload.get("iss"),
        expires_at=payload.get("exp"),
        issued_at=payload.get("iat"),
        claims=payload,
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return password_context.hash(password)
