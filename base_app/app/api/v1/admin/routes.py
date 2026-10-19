from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import CurrentAdminDep
from app.api.v1.auth.routes import AuthServiceDep
from app.schemas.auth import AdminUserUpdate, UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
async def list_users(
    service: AuthServiceDep,
    _admin: CurrentAdminDep,
) -> list[UserPublic]:
    """Everyone with an account. Admin-only — the admin user-management page."""
    users = await service.list_users()
    return [UserPublic.model_validate(user) for user in users]


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    service: AuthServiceDep,
    _admin: CurrentAdminDep,
) -> UserPublic:
    """Activate/deactivate an account, or grant/revoke admin. Admin-only.

    Refuses to remove the last remaining admin (see AuthService.update_user)
    so an admin can never accidentally lock everyone out.
    """
    user = await service.update_user(
        user_id,
        is_active=payload.is_active,
        is_admin=payload.is_admin,
    )
    return UserPublic.model_validate(user)
