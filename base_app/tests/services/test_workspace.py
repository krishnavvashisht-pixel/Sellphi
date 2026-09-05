from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.models.workspace import Workspace, WorkspacePlan, WorkspaceStatus
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from app.services.workspace import (
    WorkspaceBusinessRuleError,
    WorkspaceService,
    WorkspaceSlugConflictError,
)


class FakeWorkspaceRepository:
    def __init__(self, workspaces: list[Workspace] | None = None) -> None:
        self.workspaces = workspaces or []
        self.commits = 0
        self.rollbacks = 0

    async def create(self, workspace: Workspace) -> Workspace:
        self._hydrate(workspace)
        self.workspaces.append(workspace)
        return workspace

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[Workspace]:
        return self.workspaces[offset : offset + limit]

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        return next(
            (
                workspace
                for workspace in self.workspaces
                if workspace.id == workspace_id and workspace.deleted_at is None
            ),
            None,
        )

    async def get_by_slug(self, slug: str) -> Workspace | None:
        return next(
            (
                workspace
                for workspace in self.workspaces
                if workspace.slug == slug and workspace.deleted_at is None
            ),
            None,
        )

    async def update(self, workspace: Workspace) -> Workspace:
        workspace.updated_at = datetime.now(UTC)
        return workspace

    async def soft_delete(self, workspace: Workspace) -> Workspace:
        return workspace

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def _hydrate(self, workspace: Workspace) -> None:
        now = datetime.now(UTC)
        workspace.id = uuid4()
        workspace.created_at = now
        workspace.updated_at = now
        workspace.deleted_at = None


def make_workspace(slug: str = "existing-workspace") -> Workspace:
    now = datetime.now(UTC)
    workspace = Workspace(
        name="Existing Workspace",
        slug=slug,
        plan=WorkspacePlan.FREE,
        status=WorkspaceStatus.ACTIVE,
        settings={},
    )
    workspace.id = uuid4()
    workspace.created_at = now
    workspace.updated_at = now
    workspace.deleted_at = None
    return workspace


@pytest.mark.asyncio
async def test_create_generates_slug_when_missing() -> None:
    repository = FakeWorkspaceRepository()
    service = WorkspaceService(repository)

    workspace = await service.create(WorkspaceCreate(name="Acme Revenue Team"))

    assert workspace.slug == "acme-revenue-team"
    assert workspace.plan == WorkspacePlan.FREE
    assert workspace.status == WorkspaceStatus.ACTIVE
    assert repository.commits == 1


@pytest.mark.asyncio
async def test_create_rejects_duplicate_slug() -> None:
    repository = FakeWorkspaceRepository([make_workspace()])
    service = WorkspaceService(repository)

    with pytest.raises(WorkspaceSlugConflictError):
        await service.create(WorkspaceCreate(name="Another", slug="existing-workspace"))


@pytest.mark.asyncio
async def test_update_rejects_archived_workspace_reactivation() -> None:
    workspace = make_workspace()
    workspace.status = WorkspaceStatus.ARCHIVED
    repository = FakeWorkspaceRepository([workspace])
    service = WorkspaceService(repository)

    with pytest.raises(WorkspaceBusinessRuleError):
        await service.update(workspace.id, WorkspaceUpdate(status=WorkspaceStatus.ACTIVE))


@pytest.mark.asyncio
async def test_delete_soft_deletes_workspace() -> None:
    workspace = make_workspace()
    repository = FakeWorkspaceRepository([workspace])
    service = WorkspaceService(repository)

    await service.delete(workspace.id)

    assert workspace.deleted_at is not None
    assert repository.commits == 1
