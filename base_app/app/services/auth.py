from uuid import UUID

from fastapi import status

from app.core.exceptions import DomainError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPair


class InvalidCredentialsError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_credentials"


class InvalidRefreshTokenError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_refresh_token"


class EmailAlreadyRegisteredError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "email_already_registered"


class UserNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "user_not_found"


class CannotRemoveLastAdminError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "cannot_remove_last_admin"


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._repository.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.hashed_password):
            # Deliberately the same error for "no such user" and "wrong password"
            # so a login failure never discloses which one it was.
            raise InvalidCredentialsError("Incorrect email or password")
        return user

    async def signup(self, email: str, password: str) -> User:
        """Public registration: anyone can create their own account.

        The very first person ever to sign up is made an admin automatically
        (there's no one else yet to grant that), so there's always at least
        one admin able to manage everyone who signs up after them.
        """
        if await self._repository.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(f"{email} is already registered")

        is_first_user = await self._repository.count() == 0
        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=is_first_user,
        )
        created = await self._repository.create(user)
        await self._repository.commit()
        return created

    def issue_tokens(self, user: User) -> TokenPair:
        subject = str(user.id)
        return TokenPair(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, TokenType.REFRESH)
        if payload is None:
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        try:
            user_id = UUID(payload.subject)
        except ValueError as exc:
            raise InvalidRefreshTokenError("Invalid or expired refresh token") from exc

        user = await self._repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError("Invalid or expired refresh token")

        return self.issue_tokens(user)

    async def list_users(self) -> list[User]:
        return await self._repository.list_all()

    async def update_user(
        self,
        user_id: UUID,
        is_active: bool | None,
        is_admin: bool | None,
    ) -> User:
        """Apply an admin's change to another (or their own) account.

        Refuses any change that would leave zero active admins — otherwise
        an admin could accidentally lock everyone, including themselves,
        out of the admin page for good.
        """
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("No user with that id")

        # Primary workspace owner is permanently protected from deactivation or admin removal
        if user.email.strip().lower() == "krishnav.vashisht@gmail.com":
            if is_active is False or is_admin is False:
                raise CannotRemoveLastAdminError(
                    "Cannot remove admin or deactivate the primary workspace owner (krishnav.vashisht@gmail.com)"
                )

        would_remove_admin = (is_admin is False and user.is_admin) or (
            is_active is False and user.is_admin and (is_admin is not False)
        )
        if would_remove_admin and await self._repository.count_admins() <= 1:
            raise CannotRemoveLastAdminError(
                "Can't remove the last remaining admin — promote someone else first"
            )

        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin

        await self._repository.commit()
        return user
