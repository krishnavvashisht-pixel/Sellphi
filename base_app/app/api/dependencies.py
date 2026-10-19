from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import TokenType, decode_token
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPayload

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/token")

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
RedisDep = Annotated[Redis, Depends(get_redis_client)]


async def get_current_token_payload(
    token: Annotated[str, Depends(oauth2_scheme)],
    app_settings: SettingsDep,
) -> TokenPayload:
    payload = decode_token(token, TokenType.ACCESS, app_settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


CurrentTokenPayloadDep = Annotated[TokenPayload, Depends(get_current_token_payload)]


async def get_current_user(
    payload: CurrentTokenPayloadDep,
    db_session: DbSessionDep,
) -> User:
    """Resolve the wristband (access token) back to an actual account.

    Rejects the request the same way whether the account no longer exists
    or has been deactivated — both mean "this wristband no longer works."
    """
    try:
        user_id = UUID(payload.subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await UserRepository(db_session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUserDep) -> User:
    """Gate for admin-only pages/endpoints — the admin user-management page."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


CurrentAdminDep = Annotated[User, Depends(require_admin)]

