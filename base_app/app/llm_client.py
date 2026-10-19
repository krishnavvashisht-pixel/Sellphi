"""The one place in the app allowed to talk to an LLM SDK directly.

Every stage that needs "the Brain" (signal classification, research,
decision-maker ranking, strategy, outreach drafting, reply classification)
calls generate_structured() from here — never the google.genai SDK
directly. That's what makes swapping providers later a one-file change.
"""

from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import Settings, get_settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMNotConfiguredError(RuntimeError):
    """Raised when something tries to call Gemini without an API key set.

    Deliberately not raised at app startup (unlike the JWT secrets) —
    plenty of the app works with no Gemini key configured at all, so this
    only surfaces the moment it's actually needed.
    """


class LLMClient:
    """Thin wrapper around the Gemini SDK. Swap providers by rewriting this
    one class — nothing outside this file imports google.genai.
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate_structured(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        """Ask Gemini one question, get back one validated Pydantic object.

        Raises pydantic.ValidationError if Gemini's response doesn't match
        the requested schema — callers should let that surface rather than
        silently accepting malformed data.
        """
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        return schema.model_validate_json(response.text)


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    # Deliberately not cached: constructing genai.Client does no network
    # call, it just stores config, so there's nothing expensive to cache —
    # and caching here would need Settings to be hashable, which it isn't.
    resolved_settings = settings or get_settings()
    if resolved_settings.gemini_api_key is None:
        raise LLMNotConfiguredError(
            "GEMINI_API_KEY is not set. Add it to .env before calling any AI stage."
        )
    return LLMClient(
        api_key=resolved_settings.gemini_api_key.get_secret_value(),
        model=resolved_settings.gemini_model,
    )


async def generate_structured(
    prompt: str,
    schema: type[SchemaT],
    client: LLMClient | None = None,
) -> SchemaT:
    """The single function every pipeline stage calls to ask Gemini something.

    `client` is only ever passed explicitly in tests (to inject a fake) —
    real callers just call generate_structured(prompt, MySchema).
    """
    resolved_client = client or get_llm_client()
    return await resolved_client.generate_structured(prompt, schema)
