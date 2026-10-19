from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.saved_search import SavedSearch
from app.repositories.saved_search import SavedSearchRepository
from app.schemas.saved_search import SavedSearchCreate


@pytest.mark.asyncio
async def test_saved_search_repository_crud() -> None:
    session = AsyncMock()
    session.add = lambda inst: None
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()

    repo = SavedSearchRepository(session)
    ws_id = uuid4()
    payload = SavedSearchCreate(
        workspace_id=ws_id,
        name="Auto EV Plants India",
        query="manufacturing plant (EV OR auto) India",
        region="IN",
        limit=5,
    )

    created = await repo.create(payload)
    assert created.name == "Auto EV Plants India"
    assert created.query == "manufacturing plant (EV OR auto) India"
    assert created.region == "IN"
    assert created.limit == 5
    assert session.commit.called

    # Test delete
    await repo.delete(created)
    assert session.delete.called
    assert session.commit.call_count >= 2
