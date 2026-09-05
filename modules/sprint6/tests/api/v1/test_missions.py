from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.missions.routes import get_mission_service
from app.main import app
from app.schemas.mission import MissionCreate, MissionUpdate
from app.services.mission import (
    MissionBusinessRuleError,
    MissionICPNotFoundError,
    MissionInvalidTransitionError,
    MissionNotFoundError,
    MissionProductNotFoundError,
)


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeMissionService:
    def __init__(self) -> None:
        self.product_id = uuid4()
        self.mission_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: MissionCreate) -> object:
        return self._mission(
            product_id=payload.product_id,
            default_icp_id=payload.default_icp_id,
            name=payload.name,
            description=payload.description,
            objective=payload.objective,
            priority=payload.priority,
            execution_mode=payload.execution_mode,
            daily_prospect_limit=payload.daily_prospect_limit,
            daily_message_limit=payload.daily_message_limit,
            max_running_agents=payload.max_running_agents,
            start_date=payload.start_date,
            end_date=payload.end_date,
            timezone=payload.timezone,
            schedule=payload.schedule,
            filters=payload.filters,
            settings=payload.settings,
            created_by=payload.created_by,
        )

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: object | None = None,
    ) -> tuple[list[object], int]:
        return [self._mission(product_id=product_id)], 1

    async def get(self, mission_id: UUID, product_id: UUID | None = None) -> object:
        return self._mission(mission_id=mission_id)

    async def update(self, mission_id: UUID, payload: MissionUpdate) -> object:
        return self._mission(mission_id=mission_id, name=payload.name or "Updated Mission")

    async def delete(self, mission_id: UUID) -> None:
        self.deleted_ids.append(mission_id)

    async def pause(self, mission_id: UUID) -> object:
        return self._mission(mission_id=mission_id, status="paused")

    async def resume(self, mission_id: UUID) -> object:
        return self._mission(mission_id=mission_id, status="active")

    async def complete(self, mission_id: UUID) -> object:
        return self._mission(mission_id=mission_id, status="completed")

    async def run(self, mission_id: UUID) -> object:
        return self._mission(mission_id=mission_id, status="active", last_run_at=datetime.now(UTC))

    def _mission(
        self,
        *,
        mission_id: UUID | None = None,
        product_id: UUID | None = None,
        default_icp_id: UUID | None = None,
        name: str = "Q3 Outbound Push",
        description: str | None = None,
        objective: str | None = None,
        status: str = "draft",
        priority: object = "medium",
        execution_mode: object = "assisted",
        daily_prospect_limit: int = 50,
        daily_message_limit: int = 50,
        max_running_agents: int = 1,
        start_date: object = None,
        end_date: object = None,
        timezone: str = "UTC",
        schedule: dict | None = None,
        filters: dict | None = None,
        settings: dict | None = None,
        created_by: UUID | None = None,
        last_run_at: object = None,
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=mission_id or self.mission_id,
            product_id=product_id or self.product_id,
            default_icp_id=default_icp_id,
            name=name,
            description=description,
            objective=objective,
            status=status,
            priority=priority,
            execution_mode=execution_mode,
            daily_prospect_limit=daily_prospect_limit,
            daily_message_limit=daily_message_limit,
            max_running_agents=max_running_agents,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
            schedule=schedule or {},
            filters=filters or {},
            settings=settings or {},
            statistics={},
            last_run_at=last_run_at,
            next_run_at=None,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def mission_service() -> FakeMissionService:
    service = FakeMissionService()
    app.dependency_overrides[get_mission_service] = lambda: service
    return service


# ── POST /api/v1/missions ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.post(
        "/api/v1/missions",
        json={
            "product_id": str(mission_service.product_id),
            "name": "Q3 Outbound Push",
            "priority": "high",
            "execution_mode": "assisted",
            "daily_prospect_limit": 50,
            "daily_message_limit": 50,
            "max_running_agents": 2,
            "timezone": "UTC",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Q3 Outbound Push"
    assert data["product_id"] == str(mission_service.product_id)
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_create_mission_invalid_dates_rejected(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    response = await client.post(
        "/api/v1/missions",
        json={
            "product_id": str(mission_service.product_id),
            "name": "Bad Dates",
            "start_date": "2026-09-01",
            "end_date": "2026-08-01",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_mission_invalid_limit_rejected(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    response = await client.post(
        "/api/v1/missions",
        json={
            "product_id": str(mission_service.product_id),
            "name": "Bad Limit",
            "daily_prospect_limit": 0,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_mission_product_not_found(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    async def raise_not_found(payload: MissionCreate) -> None:
        raise MissionProductNotFoundError("Product not found")

    mission_service.create = raise_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/missions",
        json={"product_id": str(uuid4()), "name": "Mission"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_mission_icp_not_found(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    async def raise_icp_not_found(payload: MissionCreate) -> None:
        raise MissionICPNotFoundError("Default ICP not found for this product")

    mission_service.create = raise_icp_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/missions",
        json={
            "product_id": str(mission_service.product_id),
            "default_icp_id": str(uuid4()),
            "name": "Mission",
        },
    )
    assert response.status_code == 404


# ── GET /api/v1/missions ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_missions(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.get(
        "/api/v1/missions",
        params={"product_id": str(mission_service.product_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_missions_missing_product_id(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    response = await client.get("/api/v1/missions")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_missions_with_status_filter(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    response = await client.get(
        "/api/v1/missions",
        params={"product_id": str(mission_service.product_id), "status": "active"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_missions_pagination_params(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    response = await client.get(
        "/api/v1/missions",
        params={"product_id": str(mission_service.product_id), "offset": 0, "limit": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 0
    assert data["limit"] == 10


# ── GET /api/v1/missions/{id} ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.get(f"/api/v1/missions/{mission_service.mission_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(mission_service.mission_id)


@pytest.mark.asyncio
async def test_get_mission_not_found(client: AsyncClient, mission_service: FakeMissionService) -> None:
    async def raise_not_found(mission_id: UUID, product_id: UUID | None = None) -> None:
        raise MissionNotFoundError("Mission not found")

    mission_service.get = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/missions/{uuid4()}")
    assert response.status_code == 404


# ── PATCH /api/v1/missions/{id} ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.patch(
        f"/api/v1/missions/{mission_service.mission_id}",
        json={"name": "Updated Mission"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Mission"


@pytest.mark.asyncio
async def test_update_mission_business_rule_error(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    async def raise_rule_error(mission_id: UUID, payload: MissionUpdate) -> None:
        raise MissionBusinessRuleError("Cannot update an archived mission")

    mission_service.update = raise_rule_error  # type: ignore[method-assign]

    response = await client.patch(
        f"/api/v1/missions/{mission_service.mission_id}",
        json={"name": "New Name"},
    )
    assert response.status_code == 422


# ── DELETE /api/v1/missions/{id} ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.delete(f"/api/v1/missions/{mission_service.mission_id}")
    assert response.status_code == 204
    assert mission_service.mission_id in mission_service.deleted_ids


@pytest.mark.asyncio
async def test_delete_active_mission_forbidden(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    async def raise_rule_error(mission_id: UUID) -> None:
        raise MissionBusinessRuleError("Cannot delete an active mission. Pause it first.")

    mission_service.delete = raise_rule_error  # type: ignore[method-assign]

    response = await client.delete(f"/api/v1/missions/{mission_service.mission_id}")
    assert response.status_code == 422


# ── POST /api/v1/missions/{id}/pause ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_pause_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.post(f"/api/v1/missions/{mission_service.mission_id}/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_pause_mission_invalid_transition(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    async def raise_transition_error(mission_id: UUID) -> None:
        raise MissionInvalidTransitionError("Cannot pause a mission with status 'draft'")

    mission_service.pause = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/missions/{mission_service.mission_id}/pause")
    assert response.status_code == 422


# ── POST /api/v1/missions/{id}/resume ────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.post(f"/api/v1/missions/{mission_service.mission_id}/resume")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


# ── POST /api/v1/missions/{id}/complete ──────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.post(f"/api/v1/missions/{mission_service.mission_id}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


# ── POST /api/v1/missions/{id}/run ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_mission(client: AsyncClient, mission_service: FakeMissionService) -> None:
    response = await client.post(f"/api/v1/missions/{mission_service.mission_id}/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["last_run_at"] is not None


@pytest.mark.asyncio
async def test_run_mission_invalid_transition(
    client: AsyncClient, mission_service: FakeMissionService
) -> None:
    async def raise_transition_error(mission_id: UUID) -> None:
        raise MissionInvalidTransitionError("Cannot run a mission with status 'active'")

    mission_service.run = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/missions/{mission_service.mission_id}/run")
    assert response.status_code == 422
