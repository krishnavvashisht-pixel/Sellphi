from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.db.session import get_db_session
from app.main import app
from app.models.saved_search import SavedSearch


class FakeSavedSearchSession:
    def __init__(self) -> None:
        self.searches: dict[UUID, SavedSearch] = {}

    def add(self, item: SavedSearch) -> None:
        if not getattr(item, "id", None):
            item.id = uuid4()
        if not getattr(item, "created_at", None):
            item.created_at = datetime.now(UTC)
        self.searches[item.id] = item

    async def commit(self) -> None:
        pass

    async def refresh(self, item: SavedSearch) -> None:
        pass

    async def delete(self, item: SavedSearch) -> None:
        self.searches.pop(item.id, None)

    async def execute(self, statement: object) -> object:
        class FakeResult:
            def __init__(self, data: list[SavedSearch]):
                self.data = data

            def scalar_one_or_none(self) -> SavedSearch | None:
                return self.data[0] if self.data else None

            def scalars(self):
                class ScalarList:
                    def __init__(self, d: list[SavedSearch]):
                        self.d = d

                    def all(self) -> list[SavedSearch]:
                        return self.d

                return ScalarList(self.data)

        return FakeResult(list(self.searches.values()))


@pytest.mark.asyncio
async def test_saved_searches_api(client: AsyncClient) -> None:
    fake_session = FakeSavedSearchSession()
    app.dependency_overrides[get_db_session] = lambda: fake_session

    ws_id = str(uuid4())
    create_res = await client.post(
        "/api/v1/saved-searches",
        json={
            "workspace_id": ws_id,
            "name": "Auto Plants India",
            "query": "manufacturing plant EV India",
            "region": "IN",
            "limit": 5,
        },
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "Auto Plants India"
    assert created_data["region"] == "IN"
    search_id = created_data["id"]

    # List
    list_res = await client.get(f"/api/v1/saved-searches?workspace_id={ws_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Delete
    del_res = await client.delete(f"/api/v1/saved-searches/{search_id}")
    assert del_res.status_code == 204

    app.dependency_overrides.clear()
