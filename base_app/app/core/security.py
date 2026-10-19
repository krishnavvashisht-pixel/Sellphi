from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import Settings, get_settings
from app.schemas.auth import TokenPayload

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def _secret_for(token_type: TokenType, settings: Settings) -> str:
    if token_type == TokenType.ACCESS:
        return settings.jwt_access_secret_key.get_secret_value()
    return settings.jwt_refresh_secret_key.get_secret_value()


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + expires_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "token_type": token_type.value,
    }
    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, _secret_for(token_type, settings), algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    return _create_token(
        subject,
        TokenType.ACCESS,
        expires_delta or timedelta(minutes=resolved_settings.jwt_access_token_expire_minutes),
        resolved_settings,
        additional_claims,
    )


def create_refresh_token(
    subject: str,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    return _create_token(
        subject,
        TokenType.REFRESH,
        expires_delta or timedelta(minutes=resolved_settings.jwt_refresh_token_expire_minutes),
        resolved_settings,
        additional_claims,
    )


def decode_token(
    token: str,
    expected_type: TokenType,
    settings: Settings | None = None,
) -> TokenPayload | None:
    """Decode a JWT and verify it is the expected token type.

    The token_type claim is checked before anything else is trusted: a refresh
    token presented where an access token is required (or vice versa) is
    rejected even though it would otherwise decode successfully, since access
    and refresh tokens are semantically different credentials.
    """
    resolved_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            _secret_for(expected_type, resolved_settings),
            algorithms=[resolved_settings.jwt_algorithm],
            issuer=resolved_settings.jwt_issuer,
        )
    except InvalidTokenError:
        return None

    if payload.get("token_type") != expected_type.value:
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
