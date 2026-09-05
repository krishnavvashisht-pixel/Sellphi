from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.api.v1.buyer_personas.routes import get_buyer_persona_service
from app.main import app
from app.schemas.buyer_persona import BuyerPersonaCreate, BuyerPersonaUpdate
from app.services.buyer_persona import (
    BuyerPersonaBusinessRuleError,
    BuyerPersonaNotFoundError,
    BuyerPersonaProductNotFoundError,
)


# ── Fake service ──────────────────────────────────────────────────────────────

class FakeBuyerPersonaService:
    def __init__(self) -> None:
        self.product_id = uuid4()
        self.persona_id = uuid4()
        self.deleted_ids: list[UUID] = []

    async def create(self, payload: BuyerPersonaCreate) -> object:
        return self._persona(
            product_id=payload.product_id,
            name=payload.name,
            job_title=payload.job_title,
            department=payload.department,
            seniority=payload.seniority,
            buying_role=payload.buying_role,
            influence_level=payload.influence_level,
            decision_power=payload.decision_power,
            is_default=payload.is_default,
            status=payload.status,
            responsibilities=payload.responsibilities,
            business_goals=payload.business_goals,
            pain_points=payload.pain_points,
            challenges=payload.challenges,
            objections=payload.objections,
            preferred_channels=payload.preferred_channels,
            preferred_content=payload.preferred_content,
            messaging_themes=payload.messaging_themes,
            keywords=payload.keywords,
            negative_keywords=payload.negative_keywords,
            industry_notes=payload.industry_notes,
        )

    async def list(
        self,
        *,
        product_id: UUID,
        offset: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: object | None = None,
        seniority: object | None = None,
        buying_role: object | None = None,
    ) -> tuple[list[object], int]:
        return [self._persona(product_id=product_id)], 1

    async def get(self, persona_id: UUID, product_id: UUID | None = None) -> object:
        return self._persona(persona_id=persona_id)

    async def get_default_for_product(self, product_id: UUID) -> object:
        return self._persona(product_id=product_id, is_default=True)

    async def update(self, persona_id: UUID, payload: BuyerPersonaUpdate) -> object:
        return self._persona(
            persona_id=persona_id,
            name=payload.name or "Updated Persona",
            is_default=payload.is_default if payload.is_default is not None else False,
        )

    async def delete(self, persona_id: UUID) -> None:
        self.deleted_ids.append(persona_id)

    def _persona(
        self,
        *,
        persona_id: UUID | None = None,
        product_id: UUID | None = None,
        name: str = "VP of Engineering",
        job_title: str | None = "VP Engineering",
        department: str | None = "Engineering",
        seniority: object | None = None,
        buying_role: object | None = None,
        influence_level: object | None = None,
        decision_power: int | None = None,
        is_default: bool = False,
        status: object = "draft",
        responsibilities: list[str] | None = None,
        business_goals: list[str] | None = None,
        pain_points: list[str] | None = None,
        challenges: list[str] | None = None,
        objections: list[str] | None = None,
        preferred_channels: list[str] | None = None,
        preferred_content: list[str] | None = None,
        messaging_themes: list[str] | None = None,
        keywords: list[str] | None = None,
        negative_keywords: list[str] | None = None,
        industry_notes: dict | None = None,
    ) -> object:
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=persona_id or self.persona_id,
            product_id=product_id or self.product_id,
            name=name,
            job_title=job_title,
            department=department,
            seniority=seniority,
            buying_role=buying_role,
            influence_level=influence_level,
            decision_power=decision_power,
            is_default=is_default,
            status=status,
            responsibilities=responsibilities or [],
            business_goals=business_goals or [],
            pain_points=pain_points or [],
            challenges=challenges or [],
            objections=objections or [],
            preferred_channels=preferred_channels or [],
            preferred_content=preferred_content or [],
            messaging_themes=messaging_themes or [],
            keywords=keywords or [],
            negative_keywords=negative_keywords or [],
            industry_notes=industry_notes or {},
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )


@pytest.fixture
def persona_service() -> FakeBuyerPersonaService:
    service = FakeBuyerPersonaService()
    app.dependency_overrides[get_buyer_persona_service] = lambda: service
    return service


# ── POST /api/v1/buyer-personas ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_buyer_persona(client: AsyncClient, persona_service: FakeBuyerPersonaService) -> None:
    response = await client.post(
        "/api/v1/buyer-personas",
        json={
            "product_id": str(persona_service.product_id),
            "name": "VP of Engineering",
            "job_title": "VP Engineering",
            "department": "Engineering",
            "seniority": "vp",
            "buying_role": "economic_buyer",
            "influence_level": "high",
            "decision_power": 8,
            "is_default": False,
            "status": "draft",
            "responsibilities": [],
            "business_goals": [],
            "pain_points": [],
            "challenges": [],
            "objections": [],
            "preferred_channels": [],
            "preferred_content": [],
            "messaging_themes": [],
            "keywords": [],
            "negative_keywords": [],
            "industry_notes": {},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "VP of Engineering"
    assert data["product_id"] == str(persona_service.product_id)


@pytest.mark.asyncio
async def test_create_buyer_persona_invalid_decision_power_rejected(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    response = await client.post(
        "/api/v1/buyer-personas",
        json={
            "product_id": str(persona_service.product_id),
            "name": "Bad Power",
            "decision_power": 11,  # out of 1-10 range
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_buyer_persona_product_not_found(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    async def raise_not_found(payload: BuyerPersonaCreate) -> None:
        raise BuyerPersonaProductNotFoundError("Product not found")

    persona_service.create = raise_not_found  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/buyer-personas",
        json={"product_id": str(uuid4()), "name": "Persona"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_buyer_persona_duplicate_name_rejected(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    async def raise_rule_error(payload: BuyerPersonaCreate) -> None:
        raise BuyerPersonaBusinessRuleError("A buyer persona named 'Persona' already exists for this product")

    persona_service.create = raise_rule_error  # type: ignore[method-assign]

    response = await client.post(
        "/api/v1/buyer-personas",
        json={"product_id": str(persona_service.product_id), "name": "Persona"},
    )
    assert response.status_code == 422


# ── GET /api/v1/buyer-personas ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_buyer_personas(client: AsyncClient, persona_service: FakeBuyerPersonaService) -> None:
    response = await client.get(
        "/api/v1/buyer-personas",
        params={"product_id": str(persona_service.product_id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_buyer_personas_missing_product_id(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    response = await client.get("/api/v1/buyer-personas")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_buyer_personas_with_status_filter(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    response = await client.get(
        "/api/v1/buyer-personas",
        params={"product_id": str(persona_service.product_id), "status": "active"},
    )
    assert response.status_code == 200


# ── GET /api/v1/buyer-personas/{id} ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_buyer_persona(client: AsyncClient, persona_service: FakeBuyerPersonaService) -> None:
    response = await client.get(f"/api/v1/buyer-personas/{persona_service.persona_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(persona_service.persona_id)


@pytest.mark.asyncio
async def test_get_buyer_persona_not_found(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    async def raise_not_found(persona_id: UUID, product_id: UUID | None = None) -> None:
        raise BuyerPersonaNotFoundError("Buyer persona not found")

    persona_service.get = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/buyer-personas/{uuid4()}")
    assert response.status_code == 404


# ── PATCH /api/v1/buyer-personas/{id} ────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_buyer_persona(client: AsyncClient, persona_service: FakeBuyerPersonaService) -> None:
    response = await client.patch(
        f"/api/v1/buyer-personas/{persona_service.persona_id}",
        json={"name": "Updated Persona"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Persona"


@pytest.mark.asyncio
async def test_update_buyer_persona_business_rule_error(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    async def raise_rule_error(persona_id: UUID, payload: BuyerPersonaUpdate) -> None:
        raise BuyerPersonaBusinessRuleError("A buyer persona named 'X' already exists for this product")

    persona_service.update = raise_rule_error  # type: ignore[method-assign]

    response = await client.patch(
        f"/api/v1/buyer-personas/{persona_service.persona_id}",
        json={"name": "X"},
    )
    assert response.status_code == 422


# ── DELETE /api/v1/buyer-personas/{id} ───────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_buyer_persona(client: AsyncClient, persona_service: FakeBuyerPersonaService) -> None:
    response = await client.delete(f"/api/v1/buyer-personas/{persona_service.persona_id}")
    assert response.status_code == 204
    assert persona_service.persona_id in persona_service.deleted_ids


@pytest.mark.asyncio
async def test_delete_default_buyer_persona_forbidden(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    async def raise_rule_error(persona_id: UUID) -> None:
        raise BuyerPersonaBusinessRuleError("Cannot delete the default buyer persona")

    persona_service.delete = raise_rule_error  # type: ignore[method-assign]

    response = await client.delete(f"/api/v1/buyer-personas/{persona_service.persona_id}")
    assert response.status_code == 422


# ── GET /api/v1/products/{id}/default-persona ────────────────────────────────

@pytest.mark.asyncio
async def test_get_default_buyer_persona(client: AsyncClient, persona_service: FakeBuyerPersonaService) -> None:
    response = await client.get(f"/api/v1/products/{persona_service.product_id}/default-persona")
    assert response.status_code == 200
    data = response.json()
    assert data["is_default"] is True
    assert data["product_id"] == str(persona_service.product_id)


@pytest.mark.asyncio
async def test_get_default_buyer_persona_not_found(
    client: AsyncClient, persona_service: FakeBuyerPersonaService
) -> None:
    async def raise_not_found(product_id: UUID) -> None:
        raise BuyerPersonaNotFoundError("No default buyer persona found for this product")

    persona_service.get_default_for_product = raise_not_found  # type: ignore[method-assign]

    response = await client.get(f"/api/v1/products/{uuid4()}/default-persona")
    assert response.status_code == 404
