from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.api.v1.workspace.routes import get_workspace_service
from app.main import app
from app.models.workspace import WorkspacePlan, WorkspaceStatus
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from httpx import AsyncClient


class FakeWorkspaceService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: WorkspaceCreate) -> object:
        return self._workspace(
            name=payload.name,
            slug=payload.slug or "acme-team",
            plan=payload.plan,
            status=payload.status,
            settings=payload.settings,
        )

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[object]:
        return [self._workspace()]

    async def get(self, workspace_id: UUID) -> object:
        return self._workspace(workspace_id=workspace_id)

    async def update(self, workspace_id: UUID, payload: WorkspaceUpdate) -> object:
        return self._workspace(
            workspace_id=workspace_id,
            name=payload.name or "Updated Workspace",
            slug=payload.slug or "updated-workspace",
            plan=payload.plan or WorkspacePlan.PRO,
            status=payload.status or WorkspaceStatus.ACTIVE,
            settings=payload.settings or {"timezone": "UTC"},
        )

    async def delete(self, workspace_id: UUID) -> None:
        self.deleted_ids.append(workspace_id)

    def _workspace(
        self,
        *,
        workspace_id: UUID | None = None,
        name: str = "Acme Team",
        slug: str = "acme-team",
        plan: WorkspacePlan = WorkspacePlan.FREE,
        status: WorkspaceStatus = WorkspaceStatus.ACTIVE,
        settings: dict[str, object] | None = None,
    ) -> object:
        now = datetime.now(UTC)

        class WorkspaceDTO:
            id = workspace_id or self.workspace_id
            created_at = now
            updated_at = now
            deleted_at = None

        dto = WorkspaceDTO()
        dto.name = name
        dto.slug = slug
        dto.plan = plan
        dto.status = status
        dto.settings = settings or {}
        return dto


@pytest.fixture
def workspace_service() -> FakeWorkspaceService:
    service = FakeWorkspaceService()
    app.dependency_overrides[get_workspace_service] = lambda: service
    return service


@pytest.mark.asyncio
async def test_create_workspace(
    client: AsyncClient,
    workspace_service: FakeWorkspaceService,
) -> None:
    response = await client.post("/api/v1/workspaces", json={"name": "Acme Team"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Team"
    assert body["slug"] == "acme-team"
    assert body["plan"] == "free"
    assert workspace_service.deleted_ids == []


@pytest.mark.asyncio
async def test_list_workspaces(
    client: AsyncClient,
    workspace_service: FakeWorkspaceService,
) -> None:
    response = await client.get("/api/v1/workspaces")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert workspace_service.deleted_ids == []


@pytest.mark.asyncio
async def test_get_workspace(client: AsyncClient, workspace_service: FakeWorkspaceService) -> None:
    workspace_id = workspace_service.workspace_id

    response = await client.get(f"/api/v1/workspaces/{workspace_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(workspace_id)


@pytest.mark.asyncio
async def test_update_workspace(
    client: AsyncClient,
    workspace_service: FakeWorkspaceService,
) -> None:
    workspace_id = workspace_service.workspace_id

    response = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Updated Workspace", "plan": "pro"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workspace"
    assert response.json()["plan"] == "pro"


@pytest.mark.asyncio
async def test_delete_workspace(
    client: AsyncClient,
    workspace_service: FakeWorkspaceService,
) -> None:
    workspace_id = workspace_service.workspace_id

    response = await client.delete(f"/api/v1/workspaces/{workspace_id}")

    assert response.status_code == 204
    assert workspace_service.deleted_ids == [workspace_id]
