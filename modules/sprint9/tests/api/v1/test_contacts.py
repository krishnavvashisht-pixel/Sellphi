from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.contacts.routes import get_contact_service
from app.main import app
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.contact import (
    ContactBusinessRuleError,
    ContactCompanyNotFoundError,
    ContactDuplicateEmailError,
    ContactInvalidTransitionError,
    ContactNotFoundError,
)


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeContactService:
    def __init__(self) -> None:
        self.company_id = uuid4()
        self.contact_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: ContactCreate) -> object:
        return self._contact(
            company_id=payload.company_id,
            buyer_persona_id=payload.buyer_persona_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            full_name=payload.full_name or f"{payload.first_name} {payload.last_name}",
            email=payload.email,
            department=payload.department,
            relationship_status=payload.relationship_status,
            source=payload.source,
        )

    async def list(
        self,
        *,
        company_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        department: str | None = None,
        seniority: object | None = None,
        relationship_status: object | None = None,
        preferred_channel: object | None = None,
        status: object | None = None,
    ) -> tuple[list[object], int]:
        return [self._contact(company_id=company_id)], 1

    async def get(self, contact_id: UUID, company_id: UUID | None = None) -> object:
        return self._contact(contact_id=contact_id)

    async def update(self, contact_id: UUID, payload: ContactUpdate) -> object:
        return self._contact(contact_id=contact_id, first_name=payload.first_name or "Updated")

    async def delete(self, contact_id: UUID) -> None:
        self.deleted_ids.append(contact_id)

    async def archive(self, contact_id: UUID) -> object:
        return self._contact(contact_id=contact_id, status="archived")

    async def restore(self, contact_id: UUID) -> object:
        return self._contact(contact_id=contact_id, status="new")

    def _contact(
        self,
        *,
        contact_id: UUID | None = None,
        company_id: UUID | None = None,
        buyer_persona_id: UUID | None = None,
        first_name: str = "Jane",
        last_name: str = "Doe",
        full_name: str = "Jane Doe",
        email: str | None = None,
        department: str | None = None,
        relationship_status: object = "cold",
        status: object = "new",
        source: object = "manual",
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=contact_id or self.contact_id,
            company_id=company_id or self.company_id,
            buyer_persona_id=buyer_persona_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            preferred_name=None,
            job_title=None,
            department=department,
            seniority=None,
            buying_role=None,
            email=email,
            alternate_emails=[],
            phone=None,
            mobile=None,
            linkedin_url=None,
            twitter_url=None,
            location_country=None,
            location_state=None,
            location_city=None,
            timezone=None,
            languages=[],
            skills=[],
            interests=[],
            influence_score=None,
            engagement_score=None,
            confidence_score=None,
            relationship_status=relationship_status,
            preferred_channel=None,
            last_contacted_at=None,
            last_replied_at=None,
            notes=None,
            metadata_={},
            status=status,
            source=source,
            created_by=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def contact_service() -> FakeContactService:
    service = FakeContactService()
    app.dependency_overrides[get_contact_service] = lambda: service
    return service


# ── POST /api/v1/contacts ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_contact(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(contact_service.company_id),
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane@acme.com",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Jane Doe"
    assert data["company_id"] == str(contact_service.company_id)
    assert data["status"] == "new"
    assert "metadata" in data


@pytest.mark.asyncio
async def test_create_contact_invalid_email_rejected(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    response = await client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(contact_service.company_id),
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "not-an-email",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_invalid_score_rejected(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    response = await client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(contact_service.company_id),
            "first_name": "Jane",
            "last_name": "Doe",
            "influence_score": 200,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_company_not_found(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    async def raise_not_found(payload: ContactCreate) -> None:
        raise ContactCompanyNotFoundError("Company not found")

    contact_service.create = raise_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/contacts",
        json={"company_id": str(uuid4()), "first_name": "A", "last_name": "B"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_contact_duplicate_email_rejected(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    async def raise_duplicate(payload: ContactCreate) -> None:
        raise ContactDuplicateEmailError("A contact with this email already exists")

    contact_service.create = raise_duplicate  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/contacts",
        json={
            "company_id": str(contact_service.company_id),
            "first_name": "A",
            "last_name": "B",
            "email": "dup@acme.com",
        },
    )
    assert response.status_code == 422


# ── GET /api/v1/contacts ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_contacts(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.get(
        "/api/v1/contacts",
        params={"company_id": str(contact_service.company_id)},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_contacts_missing_company_id(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    response = await client.get("/api/v1/contacts")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_contacts_with_filters(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.get(
        "/api/v1/contacts",
        params={
            "company_id": str(contact_service.company_id),
            "department": "Engineering",
            "seniority": "vp",
            "relationship_status": "warm",
            "preferred_channel": "email",
            "status": "verified",
            "search": "Jane",
        },
    )
    assert response.status_code == 200


# ── GET /api/v1/contacts/{id} ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_contact(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.get(f"/api/v1/contacts/{contact_service.contact_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(contact_service.contact_id)


@pytest.mark.asyncio
async def test_get_contact_not_found(client: AsyncClient, contact_service: FakeContactService) -> None:
    async def raise_not_found(contact_id: UUID, company_id: UUID | None = None) -> None:
        raise ContactNotFoundError("Contact not found")

    contact_service.get = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/contacts/{uuid4()}")
    assert response.status_code == 404


# ── PATCH /api/v1/contacts/{id} ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_contact(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.patch(
        f"/api/v1/contacts/{contact_service.contact_id}",
        json={"first_name": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"


@pytest.mark.asyncio
async def test_update_archived_contact_rejected(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    async def raise_rule_error(contact_id: UUID, payload: ContactUpdate) -> None:
        raise ContactBusinessRuleError("Cannot update an archived contact. Restore it first.")

    contact_service.update = raise_rule_error  # type: ignore[method-assign]

    response = await client.patch(
        f"/api/v1/contacts/{contact_service.contact_id}",
        json={"job_title": "New Title"},
    )
    assert response.status_code == 422


# ── DELETE /api/v1/contacts/{id} ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_contact(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.delete(f"/api/v1/contacts/{contact_service.contact_id}")
    assert response.status_code == 204
    assert contact_service.contact_id in contact_service.deleted_ids


# ── POST /api/v1/contacts/{id}/archive ───────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_contact(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.post(f"/api/v1/contacts/{contact_service.contact_id}/archive")
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_already_archived_contact_rejected(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    async def raise_transition_error(contact_id: UUID) -> None:
        raise ContactInvalidTransitionError("Contact is already archived")

    contact_service.archive = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/contacts/{contact_service.contact_id}/archive")
    assert response.status_code == 422


# ── POST /api/v1/contacts/{id}/restore ───────────────────────────────────────

@pytest.mark.asyncio
async def test_restore_contact(client: AsyncClient, contact_service: FakeContactService) -> None:
    response = await client.post(f"/api/v1/contacts/{contact_service.contact_id}/restore")
    assert response.status_code == 200
    assert response.json()["status"] == "new"


@pytest.mark.asyncio
async def test_restore_non_archived_contact_rejected(
    client: AsyncClient, contact_service: FakeContactService
) -> None:
    async def raise_transition_error(contact_id: UUID) -> None:
        raise ContactInvalidTransitionError("Contact is not archived")

    contact_service.restore = raise_transition_error  # type: ignore[method-assign]

    response = await client.post(f"/api/v1/contacts/{contact_service.contact_id}/restore")
    assert response.status_code == 422
