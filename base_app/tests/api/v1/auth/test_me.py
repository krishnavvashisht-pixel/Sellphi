from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.api.dependencies import get_current_user
from app.main import app
from app.models.user import User
from httpx import AsyncClient


def make_user(is_admin: bool = False) -> User:
    user = User(email="someone@sellphi.dev", hashed_password="irrelevant", is_active=True, is_admin=is_admin)
    user.id = uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


@pytest.mark.asyncio
async def test_me_returns_the_current_user_without_the_password_hash(client: AsyncClient) -> None:
    user = make_user()
    app.dependency_overrides[get_current_user] = lambda: user

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "someone@sellphi.dev"
    assert "hashed_password" not in body
    assert "password" not in body


@pytest.mark.asyncio
async def test_me_without_a_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
