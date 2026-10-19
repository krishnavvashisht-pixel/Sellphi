from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.core.security import TokenType, decode_token, hash_password
from app.models.user import User
from app.services.auth import (
    AuthService,
    CannotRemoveLastAdminError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserNotFoundError,
)


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = users or []

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users if u.email == email), None)

    async def get_by_id(self, user_id: UUID) -> User | None:
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


def make_user(
    email: str = "founder@sellphi.dev",
    password: str = "correct-horse",
    active: bool = True,
    admin: bool = False,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        is_active=active,
        is_admin=admin,
    )
    user.id = uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = None
    return user


@pytest.mark.asyncio
async def test_authenticate_succeeds_with_correct_credentials() -> None:
    user = make_user(password="correct-horse")
    service = AuthService(FakeUserRepository([user]))

    authenticated = await service.authenticate("founder@sellphi.dev", "correct-horse")

    assert authenticated.id == user.id


@pytest.mark.asyncio
async def test_authenticate_rejects_wrong_password() -> None:
    user = make_user(password="correct-horse")
    service = AuthService(FakeUserRepository([user]))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("founder@sellphi.dev", "wrong-password")


@pytest.mark.asyncio
async def test_authenticate_rejects_unknown_email() -> None:
    service = AuthService(FakeUserRepository([]))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("nobody@sellphi.dev", "whatever")


@pytest.mark.asyncio
async def test_authenticate_rejects_inactive_user() -> None:
    user = make_user(password="correct-horse", active=False)
    service = AuthService(FakeUserRepository([user]))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("founder@sellphi.dev", "correct-horse")


def test_issue_tokens_returns_access_and_refresh_pair() -> None:
    user = make_user()
    service = AuthService(FakeUserRepository([user]))

    tokens = service.issue_tokens(user)

    access_payload = decode_token(tokens.access_token, TokenType.ACCESS)
    refresh_payload = decode_token(tokens.refresh_token, TokenType.REFRESH)
    assert access_payload is not None and access_payload.subject == str(user.id)
    assert refresh_payload is not None and refresh_payload.subject == str(user.id)


@pytest.mark.asyncio
async def test_refresh_issues_new_pair_from_valid_refresh_token() -> None:
    user = make_user()
    service = AuthService(FakeUserRepository([user]))
    tokens = service.issue_tokens(user)

    refreshed = await service.refresh(tokens.refresh_token)

    assert decode_token(refreshed.access_token, TokenType.ACCESS).subject == str(user.id)  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_refresh_rejects_an_access_token_used_as_a_refresh_token() -> None:
    user = make_user()
    service = AuthService(FakeUserRepository([user]))
    tokens = service.issue_tokens(user)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(tokens.access_token)


@pytest.mark.asyncio
async def test_signup_makes_the_first_ever_user_an_admin() -> None:
    service = AuthService(FakeUserRepository([]))

    user = await service.signup("founder@sellphi.dev", "correct-horse-battery")

    assert user.is_admin is True


@pytest.mark.asyncio
async def test_signup_does_not_make_later_users_admins() -> None:
    first_user = make_user(email="founder@sellphi.dev", admin=True)
    service = AuthService(FakeUserRepository([first_user]))

    second_user = await service.signup("second@sellphi.dev", "another-password")

    assert second_user.is_admin is False


@pytest.mark.asyncio
async def test_signup_rejects_an_email_already_in_use() -> None:
    existing = make_user(email="taken@sellphi.dev")
    service = AuthService(FakeUserRepository([existing]))

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.signup("taken@sellphi.dev", "some-password")


@pytest.mark.asyncio
async def test_admin_can_list_all_users() -> None:
    admin = make_user(email="admin@sellphi.dev", admin=True)
    regular = make_user(email="regular@sellphi.dev")
    service = AuthService(FakeUserRepository([admin, regular]))

    users = await service.list_users()

    assert {u.email for u in users} == {"admin@sellphi.dev", "regular@sellphi.dev"}


@pytest.mark.asyncio
async def test_admin_can_deactivate_a_regular_user() -> None:
    admin = make_user(email="admin@sellphi.dev", admin=True)
    regular = make_user(email="regular@sellphi.dev")
    service = AuthService(FakeUserRepository([admin, regular]))

    updated = await service.update_user(regular.id, is_active=False, is_admin=None)

    assert updated.is_active is False


@pytest.mark.asyncio
async def test_admin_can_promote_a_regular_user_to_admin() -> None:
    admin = make_user(email="admin@sellphi.dev", admin=True)
    regular = make_user(email="regular@sellphi.dev")
    service = AuthService(FakeUserRepository([admin, regular]))

    updated = await service.update_user(regular.id, is_active=None, is_admin=True)

    assert updated.is_admin is True


@pytest.mark.asyncio
async def test_cannot_demote_the_last_remaining_admin() -> None:
    only_admin = make_user(email="admin@sellphi.dev", admin=True)
    service = AuthService(FakeUserRepository([only_admin]))

    with pytest.raises(CannotRemoveLastAdminError):
        await service.update_user(only_admin.id, is_active=None, is_admin=False)


@pytest.mark.asyncio
async def test_cannot_deactivate_the_last_remaining_admin() -> None:
    only_admin = make_user(email="admin@sellphi.dev", admin=True)
    service = AuthService(FakeUserRepository([only_admin]))

    with pytest.raises(CannotRemoveLastAdminError):
        await service.update_user(only_admin.id, is_active=False, is_admin=None)


@pytest.mark.asyncio
async def test_can_demote_an_admin_when_another_admin_remains() -> None:
    admin_one = make_user(email="admin1@sellphi.dev", admin=True)
    admin_two = make_user(email="admin2@sellphi.dev", admin=True)
    service = AuthService(FakeUserRepository([admin_one, admin_two]))

    updated = await service.update_user(admin_one.id, is_active=None, is_admin=False)

    assert updated.is_admin is False


@pytest.mark.asyncio
async def test_update_user_raises_not_found_for_unknown_id() -> None:
    admin = make_user(email="admin@sellphi.dev", admin=True)
    service = AuthService(FakeUserRepository([admin]))

    with pytest.raises(UserNotFoundError):
        await service.update_user(uuid4(), is_active=False, is_admin=None)
