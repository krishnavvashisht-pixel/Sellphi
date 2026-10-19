import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "development", "staging", "production", "test"]


class Settings(BaseSettings):
    app_name: str = "Sellphi"
    app_version: str = "1.0.0"
    environment: Environment = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    database_url: str = "postgresql+asyncpg://sellphi:sellphi@localhost:5432/sellphi"
    database_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"

    # Optional (not required at startup like the JWT secrets): plenty of the
    # app — mission fixtures, auth, the admin page — works fine with no
    # Gemini key configured at all. app/llm_client.py raises a clear error
    # only when something actually tries to call Gemini without one.
    gemini_api_key: SecretStr | None = None
    # "Flash tier" per the build plan. Google's Flash model lineup rotates
    # every few months with real shutdown dates — check
    # https://ai.google.dev/gemini-api/docs/models before assuming this is
    # still current, and update here (one place) rather than in every module.
    gemini_model: str = "gemini-3.5-flash"

    # No default: pydantic-settings raises a ValidationError on startup if either
    # secret is missing from the environment. Access and refresh tokens are signed
    # with different keys so a leaked refresh secret can't be used to forge access
    # tokens and vice versa.
    jwt_access_secret_key: SecretStr
    jwt_refresh_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 14
    jwt_issuer: str = "sellphi"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(origin) for origin in parsed]
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
