import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_page_is_served(client: AsyncClient) -> None:
    response = await client.get("/login")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sellphi" in response.text


@pytest.mark.asyncio
async def test_admin_page_is_served(client: AsyncClient) -> None:
    response = await client.get("/admin")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_static_assets_are_served(client: AsyncClient) -> None:
    response = await client.get("/static/app.js")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_existing_json_root_endpoint_is_unaffected(client: AsyncClient) -> None:
    # The webpages must not clobber the existing API root at "/".
    response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
