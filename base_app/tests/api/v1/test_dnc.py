from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_db_session, require_admin
from app.main import app
from app.models.dnc import DncEntry
from app.models.user import User, UserRole
from app.repositories.dnc import DncRepository


class InMemoryDncSession:
    def __init__(self) -> None:
        self.dnc_entries: list[DncEntry] = []
        self.other_entries: list[object] = []

    def add(self, instance: object) -> None:
        if isinstance(instance, DncEntry):
            if instance.id is None:
                instance.id = uuid4()
            if instance.created_at is None:
                instance.created_at = datetime.now(UTC)
            self.dnc_entries.append(instance)
        else:
            self.other_entries.append(instance)

    async def flush(self) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        pass

    async def delete(self, instance: object) -> None:
        if isinstance(instance, DncEntry):
            self.dnc_entries = [e for e in self.dnc_entries if e.id != instance.id]

    async def commit(self) -> None:
        pass

    async def execute(self, statement) -> object:
        class Result:
            def __init__(self, items) -> None:
                self._items = items

            def scalar_one_or_none(self):
                return self._items[0] if self._items else None

            class Scalars:
                def __init__(self, items) -> None:
                    self._items = items

                def all(self):
                    return self._items

            def scalars(self):
                return self.Scalars(self._items)

        str_stmt = str(statement)
        if "dnc_entries.id =" in str_stmt:
            return Result(self.dnc_entries)
        return Result(self.dnc_entries)


def make_admin_user() -> User:
    user = User(
        email="admin@sellphi.dev",
        hashed_password="irrelevant",
        is_active=True,
        is_admin=True,
        role=UserRole.ADMIN.value,
    )
    user.id = uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def make_sdr_user() -> User:
    user = User(
        email="sdr@sellphi.dev",
        hashed_password="irrelevant",
        is_active=True,
        is_admin=False,
        role=UserRole.SDR.value,
    )
    user.id = uuid4()
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dnc_crud_flow_as_admin() -> None:
    session = InMemoryDncSession()
    admin_user = make_admin_user()

    app.dependency_overrides[require_admin] = lambda: admin_user
    app.dependency_overrides[get_db_session] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List initial DNC entries (should be empty)
        res = await client.get("/api/v1/admin/dnc")
        assert res.status_code == 200
        assert res.json() == []

        # 2. Add domain to DNC blacklist
        post_data = {
            "domain": "competitor.com",
            "company_name": "Competitor Corp",
            "reason": "Competitor",
        }
        res_add = await client.post("/api/v1/admin/dnc", json=post_data)
        assert res_add.status_code == 201
        data = res_add.json()
        assert data["domain"] == "competitor.com"
        assert data["company_name"] == "Competitor Corp"
        assert data["reason"] == "Competitor"
        assert data["added_by"] == admin_user.email
        dnc_id = data["id"]

        # 3. List entries again (should have 1)
        res_list = await client.get("/api/v1/admin/dnc")
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # 4. Delete the DNC entry
        res_del = await client.delete(f"/api/v1/admin/dnc/{dnc_id}")
        assert res_del.status_code == 200
        assert "removed from Do-Not-Contact list" in res_del.json()["message"]


@pytest.mark.asyncio
async def test_dnc_delete_nonexistent_returns_404() -> None:
    session = InMemoryDncSession()
    admin_user = make_admin_user()

    app.dependency_overrides[require_admin] = lambda: admin_user
    app.dependency_overrides[get_db_session] = lambda: session

    # Session with empty dnc_entries so get_by_id returns None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_id = str(uuid4())
        res = await client.delete(f"/api/v1/admin/dnc/{fake_id}")
        assert res.status_code == 404
        assert res.json()["detail"] == "DNC entry not found"


@pytest.mark.asyncio
async def test_dnc_forbidden_for_sdr() -> None:
    session = InMemoryDncSession()
    sdr_user = make_sdr_user()

    from app.api.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: sdr_user
    app.dependency_overrides[get_db_session] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Normal SDR should be forbidden from accessing admin DNC endpoints
        res = await client.get("/api/v1/admin/dnc")
        assert res.status_code == 403
        assert "Admin access required" in res.json()["detail"]
