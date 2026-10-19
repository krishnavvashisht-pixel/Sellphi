from collections.abc import AsyncIterator
from typing import Any

import pytest
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.main import app
from app.models.mission import Mission, MissionStatus
from httpx import ASGITransport, AsyncClient


class FakeDatabaseSession:
    async def execute(self, statement: Any) -> object:
        return object()


class FakeRedis:
    async def ping(self) -> bool:
        return True


async def override_db_session() -> AsyncIterator[FakeDatabaseSession]:
    yield FakeDatabaseSession()


async def override_redis_client() -> AsyncIterator[FakeRedis]:
    yield FakeRedis()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_redis_client] = override_redis_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_mission() -> Mission:
    """A realistic, ready-to-use mission for every pipeline-stage test from
    here on (signal detection, prospect discovery, research, ...) so each
    stage's tests don't have to invent their own ICP/product context.

    Field names match the product owner's confirmed icp_criteria shape
    exactly (industry, geography, company_size_range, personas, signals,
    exclusions) so this fixture path and the AI-parsed path in
    app/services/mission.py produce an equivalent, interchangeable record.

    Not persisted to a database — just a constructed object, since this
    stage is model + fixture only, no API/service layer yet.
    """
    return Mission(
        name="Find Series A SaaS companies that just raised and need a data pipeline",
        icp_criteria={
            "industry": ["B2B SaaS"],
            "geography": ["United States", "Canada"],
            "company_size_range": {"min_employees": 20, "max_employees": 200},
            "personas": ["VP of Sales", "Head of RevOps", "Director of Data Engineering"],
            "signals": [
                "Recently raised a funding round",
                "Actively hiring for data engineering roles",
                "Adopted a new data warehouse (Snowflake, BigQuery, etc.)",
            ],
            "exclusions": ["Already using a competing SDR/outbound tool"],
        },
        product_info={
            "name": "Sellphi",
            "description": "An AI SDR system that automates top-of-funnel outbound sales.",
            "value_props": [
                "Finds and researches buyers automatically",
                "Personalized outreach at the speed of software",
            ],
        },
        status=MissionStatus.ACTIVE,
    )
