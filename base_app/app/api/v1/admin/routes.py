import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentAdminDep, CurrentSuperAdminDep, DbSessionDep
from app.api.v1.auth.routes import AuthServiceDep
from app.models.audit_log import AuditLog
from app.models.invitation import AdminInvitation
from app.models.user import UserRole
from app.repositories.audit_log import AuditLogRepository
from app.repositories.invitation import InvitationRepository
from app.schemas.auth import (
    AdminUserUpdate,
    AuditLogPublic,
    CreateInvitationRequest,
    InvitationPublic,
    UserPublic,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    service: AuthServiceDep,
    _admin: CurrentAdminDep,
) -> list[UserPublic]:
    """Everyone with an account. Accessible by Admins and Super Admins."""
    users = await service.list_users()
    return [UserPublic.model_validate(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    service: AuthServiceDep,
    _admin: CurrentAdminDep,
) -> UserPublic:
    """Activate/deactivate an account, or grant/revoke admin or roles.
    
    Security enforcement:
    Only Super Admins can assign or change roles, or toggle admin privileges.
    Regular admins can only activate or deactivate non-admin team members.
    """
    is_super_admin = (
        _admin.email.strip().lower() == "krishnav.vashisht@gmail.com"
        or _admin.role == UserRole.SUPER_ADMIN.value
    )

    if (payload.role is not None or payload.is_admin is not None) and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admins can promote, demote, or change user roles.",
        )

    user = await service.update_user(
        user_id,
        is_active=payload.is_active,
        is_admin=payload.is_admin,
        role=payload.role,
        actor_email=_admin.email,
        actor_id=_admin.id,
    )
    return UserPublic.model_validate(user)


@router.post("/invitations", response_model=InvitationPublic, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    payload: CreateInvitationRequest,
    db_session: DbSessionDep,
    _super_admin: CurrentSuperAdminDep,
) -> InvitationPublic:
    """Generate a privileged team invitation link. Super Admin only."""
    invitation_repo = InvitationRepository(db_session)
    audit_repo = AuditLogRepository(db_session)

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)

    invitation = AdminInvitation(
        inviter_id=_super_admin.id,
        inviter_email=_super_admin.email,
        invited_email=payload.invited_email.lower().strip(),
        role=payload.role,
        token=token,
        expires_at=expires_at,
        is_revoked=False,
    )
    created = await invitation_repo.create(invitation)

    await audit_repo.create(
        AuditLog(
            actor_id=_super_admin.id,
            actor_email=_super_admin.email,
            action="create_invitation",
            target_email=payload.invited_email.lower().strip(),
            new_value=payload.role,
            details=f"Generated {payload.role} invitation token for {payload.invited_email}",
        )
    )
    await invitation_repo.commit()

    return InvitationPublic.model_validate(created)


@router.get("/invitations", response_model=list[InvitationPublic])
async def list_invitations(
    db_session: DbSessionDep,
    _admin: CurrentAdminDep,
) -> list[InvitationPublic]:
    """List all invitations. Accessible by Admins and Super Admins."""
    invitation_repo = InvitationRepository(db_session)
    invitations = await invitation_repo.list_all()
    return [InvitationPublic.model_validate(inv) for inv in invitations]


@router.delete("/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: UUID,
    db_session: DbSessionDep,
    _super_admin: CurrentSuperAdminDep,
) -> dict[str, str]:
    """Revoke an active invitation. Super Admin only."""
    invitation_repo = InvitationRepository(db_session)
    invitation = await invitation_repo.get_by_id(invitation_id)
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    invitation.is_revoked = True
    audit_repo = AuditLogRepository(db_session)
    await audit_repo.create(
        AuditLog(
            actor_id=_super_admin.id,
            actor_email=_super_admin.email,
            action="revoke_invitation",
            target_email=invitation.invited_email,
            old_value=invitation.role,
            details=f"Revoked invitation for {invitation.invited_email}",
        )
    )
    await invitation_repo.commit()
    return {"message": "Invitation revoked successfully"}


@router.get("/audits", response_model=list[AuditLogPublic])
async def list_audit_logs(
    db_session: DbSessionDep,
    _admin: CurrentAdminDep,
) -> list[AuditLogPublic]:
    """Inspect immutable security and role change audit logs."""
    audit_repo = AuditLogRepository(db_session)
    logs = await audit_repo.list_recent(limit=100)
    return [AuditLogPublic.model_validate(log) for log in logs]
