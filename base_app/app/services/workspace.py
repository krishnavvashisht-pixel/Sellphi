import re
from uuid import UUID

from app.core.exceptions import (
    BusinessRuleViolationError,
    EntityConflictError,
    EntityNotFoundError,
)
from app.models.workspace import Workspace, WorkspaceStatus
from app.repositories.workspace import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.utils.time import utc_now

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkspaceNotFoundError(EntityNotFoundError):
    error_code = "workspace_not_found"


class WorkspaceSlugConflictError(EntityConflictError):
    error_code = "workspace_slug_conflict"


class WorkspaceBusinessRuleError(BusinessRuleViolationError):
    error_code = "workspace_business_rule_violation"


class WorkspaceService:
    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    async def create(self, payload: WorkspaceCreate) -> Workspace:
        slug = self._normalize_slug(payload.slug or self._slugify(payload.name))
        await self._ensure_slug_available(slug)
        self._validate_status_transition(None, payload.status)

        workspace = Workspace(
            name=payload.name,
            slug=slug,
            plan=payload.plan,
            status=payload.status,
            settings=payload.settings,
        )

        try:
            created = await self._repository.create(workspace)
            await self._repository.commit()
        except Exception:
            await self._repository.rollback()
            raise

        return created

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[Workspace]:
        return await self._repository.list(offset=offset, limit=limit)

    async def get(self, workspace_id: UUID) -> Workspace:
        workspace = await self._repository.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError("Workspace not found")
        return workspace

    async def update(self, workspace_id: UUID, payload: WorkspaceUpdate) -> Workspace:
        workspace = await self.get(workspace_id)
        updates = payload.model_dump(exclude_unset=True)

        if "slug" in updates:
            next_slug = self._normalize_slug(updates["slug"])
            if next_slug != workspace.slug:
                await self._ensure_slug_available(next_slug, exclude_id=workspace.id)
            workspace.slug = next_slug

        if "name" in updates:
            workspace.name = updates["name"]

        if "plan" in updates:
            workspace.plan = updates["plan"]

        if "status" in updates:
            self._validate_status_transition(workspace.status, updates["status"])
            workspace.status = updates["status"]

        if "settings" in updates:
            workspace.settings = updates["settings"]

        try:
            updated = await self._repository.update(workspace)
            await self._repository.commit()
        except Exception:
            await self._repository.rollback()
            raise

        return updated

    async def delete(self, workspace_id: UUID) -> None:
        workspace = await self.get(workspace_id)
        workspace.deleted_at = utc_now()

        try:
            await self._repository.soft_delete(workspace)
            await self._repository.commit()
        except Exception:
            await self._repository.rollback()
            raise

    async def _ensure_slug_available(self, slug: str, exclude_id: UUID | None = None) -> None:
        existing = await self._repository.get_by_slug(slug)
        if existing is not None and existing.id != exclude_id:
            raise WorkspaceSlugConflictError("Workspace slug already exists")

    def _normalize_slug(self, slug: str) -> str:
        normalized = self._slugify(slug)
        if not normalized or not SLUG_PATTERN.fullmatch(normalized):
            raise WorkspaceBusinessRuleError(
                "Workspace slug must contain lowercase letters, numbers, and hyphens"
            )
        return normalized

    def _slugify(self, value: str) -> str:
        lowered = value.strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", lowered)
        return slug.strip("-")

    def _validate_status_transition(
        self,
        current_status: WorkspaceStatus | None,
        next_status: WorkspaceStatus,
    ) -> None:
        if current_status == WorkspaceStatus.ARCHIVED and next_status != WorkspaceStatus.ARCHIVED:
            raise WorkspaceBusinessRuleError("Archived workspaces cannot be reactivated")
