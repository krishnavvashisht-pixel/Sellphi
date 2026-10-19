from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.api.dependencies import get_current_user, require_admin
from app.api.v1.auth.routes import get_auth_service
from app.main import app
from app.models.user import User
from httpx import AsyncClient


def make_user(email: str = "someone@sellphi.dev", is_admin: bool = False) -> User:
    user = User(email=email, hashed_password="irrelevant", is_active=True, is_admin=is_admin)
    user.id = uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


class FakeAuthService:
    def __init__(self, users: list[User]) -> None:
        self.users = users

    async def list_users(self) -> list[User]:
        return self.users

    async def update_user(self, user_id, is_active, is_admin) -> User:  # noqa: ANN001
        user = next(u for u in self.users if u.id == user_id)
        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        return user


@pytest.mark.asyncio
async def test_admin_can_list_users(client: AsyncClient) -> None:
    admin = make_user("admin@sellphi.dev", is_admin=True)
    regular = make_user("regular@sellphi.dev")
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService([admin, regular])

    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 200
    assert {u["email"] for u in response.json()} == {"admin@sellphi.dev", "regular@sellphi.dev"}


@pytest.mark.asyncio
async def test_listing_users_without_a_token_is_rejected(client: AsyncClient) -> None:
    # No override for require_admin here: proves the route genuinely requires
    # a logged-in user (and, in the real app, an admin one) rather than being
    # open by accident.
    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_a_logged_in_non_admin_is_forbidden_from_listing_users(client: AsyncClient) -> None:
    # Override get_current_user (not require_admin) so the real require_admin
    # dependency actually runs and does the rejecting — this is the check
    # that matters: a real, logged-in, non-admin account must be refused.
    regular = make_user("regular@sellphi.dev", is_admin=False)
    app.dependency_overrides[get_current_user] = lambda: regular

    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_deactivate_a_user(client: AsyncClient) -> None:
    admin = make_user("admin@sellphi.dev", is_admin=True)
    regular = make_user("regular@sellphi.dev")
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService([admin, regular])

    response = await client.patch(
        f"/api/v1/admin/users/{regular.id}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False
