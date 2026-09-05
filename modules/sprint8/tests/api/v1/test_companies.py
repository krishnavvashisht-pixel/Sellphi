from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.companies.routes import get_company_service
from app.main import app
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company import (
    CompanyBusinessRuleError,
    CompanyDuplicateDomainError,
    CompanyInvalidTransitionError,
    CompanyMissionNotFoundError,
    CompanyNotFoundError,
    CompanyWorkspaceNotFoundError,
)


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeCompanyService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.company_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: CompanyCreate) -> object:
        return self._company(
            workspace_id=payload.workspace_id,
            mission_id=payload.mission_id,
            name=payload.name,
            website=payload.website,
            domain=payload.domain,
            industry=payload.industry,
            funding_stage=payload.funding_stage,
            health_score=payload.health_score,
            fit_score=payload.fit_score,
            engagement_score=payload.engagement_score,
            confidence_score=payload.confidence_score,
            source=payload.source,
            created_by=payload.created_by,
        )

    async def list(
        self,
        *,
        workspace_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        industry: str | None = None,
        status: object | None = None,
        funding_stage: object | None = None,
        company_size: str | None = None,
        country: str | None = None,
        mission_id: UUID | None = None,
    ) -> tuple[list[object], int]:
        return [self._company(workspace_id=workspace_id)], 1

    async def get(self, company_id: UUID, workspace_id: UUID | None = None) -> object:
        return self._company(company_id=company_id)

    async def update(self, company_id: UUID, payload: CompanyUpdate) -> object:
        return self._company(company_id=company_id, name=payload.name or "Updated Company")

    async def delete(self, company_id: UUID) -> None:
        self.deleted_ids.append(company_id)

    async def archive(self, company_id: UUID) -> object:
        return self._company(company_id=company_id, status="archived")

    async def restore(self, company_id: UUID) -> object:
        return self._company(company_id=company_id, status="new")

    def _company(
        self,
        *,
        company_id: UUID | None = None,
        workspace_id: UUID | None = None,
        mission_id: UUID | None = None,
        name: str = "Acme Corp",
        website: str | None = None,
        domain: str | None = None,
        industry: str | None = None,
        funding_stage: object = None,
        health_score: int | None = None,
        fit_score: int | None = None,
        engagement_score: int | None = None,
        confidence_score: int | None = None,
        status: object = "new",
        source: object = "manual",
        created_by: UUID | None = None,
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=company_id or self.company_id,
            workspace_id=workspace_id or self.workspace_id,
            mission_id=mission_id,
            name=name,
            legal_name=None,
            website=website,
            domain=domain,
            linkedin_url=None,
            industry=industry,
            sub_industry=None,
            company_size=None,
            annual_revenue=None,
            headquarters_country=None,
            headquarters_state=None,
            headquarters_city=None,
            founded_year=None,
            company_type=None,
            ownership_type=None,
            stock_symbol=None,
            funding_stage=funding_stage,
            technologies=[],
            description=None,
            summary=None,
            tags=[],
            metadata_={},
            health_score=health_score,
            fit_score=fit_score,
            engagement_score=engagement_score,
            confidence_score=confidence_score,
            status=status,
            source=source,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def company_service() -> FakeCompanyService:
    service = FakeCompanyService()
    app.dependency_overrides[get_company_service] = lambda: service
    return service


# ── POST /api/v1/companies ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_company(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.post(
        "/api/v1/companies",
        json={
            "workspace_id": str(company_service.workspace_id),
            "name": "Acme Corp",
            "website": "https://acme.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert data["workspace_id"] == str(company_service.workspace_id)
    assert data["status"] == "new"
    assert "metadata" in data


@pytest.mark.asyncio
async def test_create_company_invalid_score_rejected(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    response = await client.post(
        "/api/v1/companies",
        json={
            "workspace_id": str(company_service.workspace_id),
            "name": "Bad Score Co",
            "fit_score": 150,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_company_workspace_not_found(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    async def raise_not_found(payload: CompanyCreate) -> None:
        raise CompanyWorkspaceNotFoundError("Workspace not found")

    company_service.create = raise_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/companies",
        json={"workspace_id": str(uuid4()), "name": "Co"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_company_duplicate_domain_rejected(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    async def raise_duplicate(payload: CompanyCreate) -> None:
        raise CompanyDuplicateDomainError("A company with this domain already exists")

    company_service.create = raise_duplicate  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/companies",
        json={
            "workspace_id": str(company_service.workspace_id),
            "name": "Duplicate Co",
            "website": "https://acme.com",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_company_invalid_mission_rejected(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    async def raise_mission_not_found(payload: CompanyCreate) -> None:
        raise CompanyMissionNotFoundError("Mission does not belong to this workspace")

    company_service.create = raise_mission_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/companies",
        json={
            "workspace_id": str(company_service.workspace_id),
            "mission_id": str(uuid4()),
            "name": "Co",
        },
    )
    assert response.status_code == 404


# ── GET /api/v1/companies ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_companies(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.get(
        "/api/v1/companies",
        params={"workspace_id": str(company_service.workspace_id)},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_companies_missing_workspace_id(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    response = await client.get("/api/v1/companies")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_companies_with_filters(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.get(
        "/api/v1/companies",
        params={
            "workspace_id": str(company_service.workspace_id),
            "industry": "Software",
            "status": "qualified",
            "funding_stage": "series_a",
            "company_size": "51-200",
            "country": "United States",
            "mission_id": str(uuid4()),
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_companies_with_search(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.get(
        "/api/v1/companies",
        params={"workspace_id": str(company_service.workspace_id), "search": "Acme"},
    )
    assert response.status_code == 200


# ── GET /api/v1/companies/{id} ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_company(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.get(f"/api/v1/companies/{company_service.company_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(company_service.company_id)


@pytest.mark.asyncio
async def test_get_company_not_found(client: AsyncClient, company_service: FakeCompanyService) -> None:
    async def raise_not_found(company_id: UUID, workspace_id: UUID | None = None) -> None:
        raise CompanyNotFoundError("Company not found")

    company_service.get = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/companies/{uuid4()}")
    assert response.status_code == 404


# ── PATCH /api/v1/companies/{id} ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_company(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.patch(
        f"/api/v1/companies/{company_service.company_id}",
        json={"name": "Updated Company"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Company"


@pytest.mark.asyncio
async def test_update_archived_company_rejected(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    async def raise_rule_error(company_id: UUID, payload: CompanyUpdate) -> None:
        raise CompanyBusinessRuleError("Cannot update an archived company. Restore it first.")

    company_service.update = raise_rule_error  # type: ignore[method-assign]

    response = await client.patch(
        f"/api/v1/companies/{company_service.company_id}",
        json={"name": "New Name"},
    )
    assert response.status_code == 422


# ── DELETE /api/v1/companies/{id} ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_company(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.delete(f"/api/v1/companies/{company_service.company_id}")
    assert response.status_code == 204
    assert company_service.company_id in company_service.deleted_ids


# ── POST /api/v1/companies/{id}/archive ──────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_company(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.post(f"/api/v1/companies/{company_service.company_id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_already_archived_company_rejected(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    async def raise_transition_error(company_id: UUID) -> None:
        raise CompanyInvalidTransitionError("Company is already archived")

    company_service.archive = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/companies/{company_service.company_id}/archive")
    assert response.status_code == 422


# ── POST /api/v1/companies/{id}/restore ──────────────────────────────────────

@pytest.mark.asyncio
async def test_restore_company(client: AsyncClient, company_service: FakeCompanyService) -> None:
    response = await client.post(f"/api/v1/companies/{company_service.company_id}/restore")
    assert response.status_code == 200
    assert response.json()["status"] == "new"


@pytest.mark.asyncio
async def test_restore_non_archived_company_rejected(
    client: AsyncClient, company_service: FakeCompanyService
) -> None:
    async def raise_transition_error(company_id: UUID) -> None:
        raise CompanyInvalidTransitionError("Company is not archived")

    company_service.restore = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/companies/{company_service.company_id}/restore")
    assert response.status_code == 422
