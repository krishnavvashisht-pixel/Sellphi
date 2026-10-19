import pytest
from app.core.config import Settings
from app.llm_client import LLMClient, LLMNotConfiguredError, generate_structured, get_llm_client
from pydantic import BaseModel


class Animal(BaseModel):
    name: str
    legs: int


class FakeGeminiClient:
    """Stands in for LLMClient in tests — no real network call to Google."""

    def __init__(self, canned_response: str) -> None:
        self.canned_response = canned_response
        self.calls: list[tuple[str, type[BaseModel]]] = []

    async def generate_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        self.calls.append((prompt, schema))
        return schema.model_validate_json(self.canned_response)


def make_settings(gemini_api_key: str | None = None) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        jwt_access_secret_key="access-secret",
        jwt_refresh_secret_key="refresh-secret",
        gemini_api_key=gemini_api_key,
    )


def test_get_llm_client_raises_a_clear_error_with_no_api_key() -> None:
    settings = make_settings(gemini_api_key=None)

    with pytest.raises(LLMNotConfiguredError):
        get_llm_client(settings)


def test_get_llm_client_returns_a_configured_client_with_a_key() -> None:
    settings = make_settings(gemini_api_key="fake-key")

    client = get_llm_client(settings)

    assert isinstance(client, LLMClient)


@pytest.mark.asyncio
async def test_generate_structured_returns_a_validated_object() -> None:
    fake_client = FakeGeminiClient('{"name": "dog", "legs": 4}')

    result = await generate_structured("describe a dog", Animal, client=fake_client)  # type: ignore[arg-type]

    assert result == Animal(name="dog", legs=4)
    assert fake_client.calls == [("describe a dog", Animal)]


@pytest.mark.asyncio
async def test_generate_structured_raises_on_a_response_that_does_not_match_the_schema() -> None:
    fake_client = FakeGeminiClient('{"name": "dog"}')  # missing required "legs"

    with pytest.raises(Exception):  # pydantic.ValidationError
        await generate_structured("describe a dog", Animal, client=fake_client)  # type: ignore[arg-type]
