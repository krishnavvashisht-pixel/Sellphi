from uuid import uuid4

import pytest
from app.api.v1.auth.routes import get_auth_service
from app.main import app
from app.schemas.auth import TokenPair
from app.services.auth import EmailAlreadyRegisteredError, InvalidCredentialsError, InvalidRefreshTokenError
from httpx import AsyncClient


class FakeAuthService:
    def __init__(self) -> None:
        self.user_id = uuid4()
        self.registered_emails: set[str] = set()

    async def signup(self, email: str, password: str) -> object:
        if email in self.registered_emails:
            raise EmailAlreadyRegisteredError(f"{email} is already registered")
        self.registered_emails.add(email)
        return object()

    async def authenticate(self, email: str, password: str) -> object:
        if email != "founder@sellphi.dev" or password != "correct-horse":
            raise InvalidCredentialsError("Incorrect email or password")
        return object()

    def issue_tokens(self, user: object) -> TokenPair:
        return TokenPair(access_token="fake-access-token", refresh_token="fake-refresh-token")

    async def refresh(self, refresh_token: str) -> TokenPair:
        if refresh_token != "fake-refresh-token":
            raise InvalidRefreshTokenError("Invalid or expired refresh token")
        return TokenPair(access_token="new-access-token", refresh_token="new-refresh-token")


@pytest.fixture
def auth_service() -> FakeAuthService:
    service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    return service


@pytest.mark.asyncio
async def test_signup_returns_token_pair(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "new-person@sellphi.dev", "password": "correct-horse-battery"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-access-token"


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    await client.post(
        "/api/v1/auth/signup",
        json={"email": "taken@sellphi.dev", "password": "correct-horse-battery"},
    )

    second_attempt = await client.post(
        "/api/v1/auth/signup",
        json={"email": "taken@sellphi.dev", "password": "another-password"},
    )

    assert second_attempt.status_code == 409


@pytest.mark.asyncio
async def test_signup_rejects_a_too_short_password(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    response = await client.post(
        "/api/v1/auth/signup",
        json={"email": "new-person@sellphi.dev", "password": "short"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_with_correct_credentials_returns_token_pair(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "founder@sellphi.dev", "password": "correct-horse"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "fake-access-token"
    assert body["refresh_token"] == "fake-refresh-token"
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "founder@sellphi.dev", "password": "wrong"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_valid_refresh_token_returns_new_pair(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "fake-refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access-token"


@pytest.mark.asyncio
async def test_refresh_with_invalid_refresh_token_returns_401(
    client: AsyncClient,
    auth_service: FakeAuthService,
) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "garbage"},
    )

    assert response.status_code == 401
