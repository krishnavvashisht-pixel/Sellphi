from collections.abc import AsyncIterator
from typing import Any

import pytest
from app.db.redis import get_redis_client
from app.db.session import get_db_session
from app.main import app
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
