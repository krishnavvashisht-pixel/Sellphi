from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import CurrentUserDep, DbSessionDep
from app.repositories.user import UserRepository
from app.schemas.auth import RefreshTokenRequest, SignupRequest, TokenPair, UserPublic
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db_session: DbSessionDep) -> AuthService:
    repository = UserRepository(db_session)
    return AuthService(repository)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/signup", response_model=TokenPair)
async def signup(
    payload: SignupRequest,
    service: AuthServiceDep,
) -> TokenPair:
    """Public registration. The first person ever to sign up becomes an admin."""
    user = await service.signup(payload.email, payload.password)
    return service.issue_tokens(user)


@router.post("/token", response_model=TokenPair)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> TokenPair:
    user = await service.authenticate(form_data.username, form_data.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.refresh(payload.refresh_token)


@router.get("/me", response_model=UserPublic)
async def read_current_user(current_user: CurrentUserDep) -> UserPublic:
    return UserPublic.model_validate(current_user)
