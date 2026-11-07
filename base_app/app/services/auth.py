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
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.repositories.audit_log import AuditLogRepository
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
    def __init__(
        self,
        repository: UserRepository,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self._repository = repository
        self._audit_repo = audit_repo or (
            AuditLogRepository(repository._session) if hasattr(repository, "_session") else None
        )

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._repository.get_by_email(email)
        if user is None or not user.is_active or not verify_password(password, user.hashed_password):
            # Deliberately the same error for "no such user" and "wrong password"
            # so a login failure never discloses which one it was.
            raise InvalidCredentialsError("Incorrect email or password")
        return user

    async def signup(self, email: str, password: str, role: str | None = None) -> User:
        """Public or invitation registration.
        
        The very first person ever to sign up is made a super admin automatically
        (if database is empty), otherwise defaults to standard SDR role.
        """
        if await self._repository.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(f"{email} is already registered")

        if role is not None:
            user_role = role
            is_admin = role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]
        else:
            is_first_user = await self._repository.count() == 0
            is_admin = is_first_user
            user_role = UserRole.SUPER_ADMIN.value if is_first_user else UserRole.SDR.value

        user = User(
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=is_admin,
            role=user_role,
        )
        created = await self._repository.create(user)

        # Log creation to audit trail
        if self._audit_repo:
            try:
                await self._audit_repo.create(
                    AuditLog(
                        actor_id=created.id,
                        actor_email=created.email,
                        action="signup",
                        target_user_id=created.id,
                        target_email=created.email,
                        new_value=user_role,
                        details=f"Account created with role: {user_role}",
                    )
                )
            except Exception:
                pass

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
        is_active: bool | None = None,
        is_admin: bool | None = None,
        role: str | None = None,
        actor_email: str | None = None,
        actor_id: UUID | None = None,
    ) -> User:
        """Apply an admin's change to another (or their own) account.

        Refuses any change that would leave zero active admins — otherwise
        an admin could accidentally lock everyone, including themselves,
        out of the admin page for good.

        Protects the primary workspace owner (krishnav.vashisht@gmail.com)
        from ever being demoted, modified away from super_admin, or deactivated.
        """
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("No user with that id")

        # Primary workspace owner is permanently protected from deactivation, demotion, or admin removal
        if user.email.strip().lower() == "krishnav.vashisht@gmail.com":
            if is_active is False or is_admin is False or (role is not None and role != UserRole.SUPER_ADMIN.value):
                raise CannotRemoveLastAdminError(
                    "Cannot remove admin, demote, or deactivate the primary workspace owner (krishnav.vashisht@gmail.com)"
                )

        would_remove_admin = (
            (is_admin is False and user.is_admin)
            or (is_active is False and user.is_admin and (is_admin is not False))
            or (role is not None and role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value] and user.is_admin)
        )
        if would_remove_admin and await self._repository.count_admins() <= 1:
            raise CannotRemoveLastAdminError(
                "Can't remove the last remaining admin — promote someone else first"
            )

        actor = actor_email or "system"

        if role is not None and role != user.role:
            old_role = user.role
            user.role = role
            user.is_admin = role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]
            if self._audit_repo:
                try:
                    await self._audit_repo.create(
                        AuditLog(
                            actor_id=actor_id,
                            actor_email=actor,
                            action="role_change",
                            target_user_id=user.id,
                            target_email=user.email,
                            old_value=old_role,
                            new_value=role,
                            details=f"Role changed from {old_role} to {role} by {actor}",
                        )
                    )
                except Exception:
                    pass

        if is_admin is not None and is_admin != user.is_admin:
            old_admin = str(user.is_admin)
            user.is_admin = is_admin
            if is_admin and user.role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
                user.role = UserRole.ADMIN.value
            elif not is_admin and user.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
                user.role = UserRole.SDR.value
            if self._audit_repo:
                try:
                    await self._audit_repo.create(
                        AuditLog(
                            actor_id=actor_id,
                            actor_email=actor,
                            action="admin_toggle",
                            target_user_id=user.id,
                            target_email=user.email,
                            old_value=old_admin,
                            new_value=str(is_admin),
                            details=f"Admin status toggled to {is_admin} by {actor}",
                        )
                    )
                except Exception:
                    pass

        if is_active is not None and is_active != user.is_active:
            old_active = str(user.is_active)
            user.is_active = is_active
            if self._audit_repo:
                try:
                    await self._audit_repo.create(
                        AuditLog(
                            actor_id=actor_id,
                            actor_email=actor,
                            action="status_change",
                            target_user_id=user.id,
                            target_email=user.email,
                            old_value=old_active,
                            new_value=str(is_active),
                            details=f"Active status changed to {is_active} by {actor}",
                        )
                    )
                except Exception:
                    pass

        await self._repository.commit()
        return user
