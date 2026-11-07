from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.api.dependencies import get_current_user, require_admin, require_super_admin
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole
from app.services.auth import CannotRemoveLastAdminError
from httpx import AsyncClient


def make_user(
    email: str = "someone@sellphi.dev",
    is_admin: bool = False,
    role: str = "sdr",
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("correct-horse"),
        is_active=True,
        is_admin=is_admin,
        role=role,
    )
    user.id = uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = users or []

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users if u.email == email), None)

    async def get_by_id(self, user_id) -> User | None:
        return next((u for u in self.users if u.id == user_id), None)

    async def count(self) -> int:
        return len(self.users)

    async def count_admins(self) -> int:
        return sum(1 for u in self.users if u.is_admin)

    async def list_all(self) -> list[User]:
        return list(self.users)

    async def create(self, user: User) -> User:
        user.id = user.id or uuid4()
        self.users.append(user)
        return user

    async def commit(self) -> None:
        pass


@pytest.mark.asyncio
async def test_first_user_signup_becomes_super_admin() -> None:
    from app.services.auth import AuthService
    repo = FakeUserRepository([])
    service = AuthService(repo)

    user = await service.signup("founder@sellphi.dev", "correct-horse-battery")

    assert user.is_admin is True
    assert user.role == UserRole.SUPER_ADMIN.value


@pytest.mark.asyncio
async def test_subsequent_user_signup_defaults_to_sdr() -> None:
    from app.services.auth import AuthService
    founder = make_user("founder@sellphi.dev", is_admin=True, role="super_admin")
    repo = FakeUserRepository([founder])
    service = AuthService(repo)

    new_user = await service.signup("sales.rep@sellphi.dev", "correct-horse-battery")

    assert new_user.is_admin is False
    assert new_user.role == UserRole.SDR.value


@pytest.mark.asyncio
async def test_protected_super_admin_cannot_be_demoted_or_deactivated() -> None:
    from app.services.auth import AuthService
    owner = make_user("krishnav.vashisht@gmail.com", is_admin=True, role="super_admin")
    admin2 = make_user("admin2@sellphi.dev", is_admin=True, role="admin")
    repo = FakeUserRepository([owner, admin2])
    service = AuthService(repo)

    # Demoting role away from super_admin must fail
    with pytest.raises(CannotRemoveLastAdminError):
        await service.update_user(owner.id, role="admin")

    # Demoting admin flag must fail
    with pytest.raises(CannotRemoveLastAdminError):
        await service.update_user(owner.id, is_admin=False)

    # Deactivating owner must fail
    with pytest.raises(CannotRemoveLastAdminError):
        await service.update_user(owner.id, is_active=False)


@pytest.mark.asyncio
async def test_super_admin_can_promote_and_demote_team_members() -> None:
    from app.services.auth import AuthService
    owner = make_user("krishnav.vashisht@gmail.com", is_admin=True, role="super_admin")
    rep = make_user("rep@sellphi.dev", is_admin=False, role="sdr")
    repo = FakeUserRepository([owner, rep])
    service = AuthService(repo)

    # Promote SDR to Admin
    updated = await service.update_user(rep.id, role="admin")
    assert updated.role == "admin"
    assert updated.is_admin is True

    # Demote Admin back to SDR
    demoted = await service.update_user(rep.id, role="sdr")
    assert demoted.role == "sdr"
    assert demoted.is_admin is False


@pytest.mark.asyncio
async def test_non_admin_cannot_access_invitations_api(client: AsyncClient) -> None:
    rep = make_user("rep@sellphi.dev", role="sdr")
    app.dependency_overrides[get_current_user] = lambda: rep

    response = await client.get("/api/v1/admin/invitations")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_regular_admin_cannot_create_invitation_only_super_admin(client: AsyncClient) -> None:
    admin = make_user("admin@sellphi.dev", is_admin=True, role="admin")
    app.dependency_overrides[get_current_user] = lambda: admin

    response = await client.post(
        "/api/v1/admin/invitations",
        json={"invited_email": "newbie@sellphi.dev", "role": "admin"},
    )
    assert response.status_code == 403
    assert "Super Admin" in response.json()["detail"]
