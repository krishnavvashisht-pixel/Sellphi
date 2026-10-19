import pytest
from app.core.config import Settings
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from pydantic import ValidationError


def make_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "jwt_access_secret_key": "access-secret",
        "jwt_refresh_secret_key": "refresh-secret",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


def test_settings_requires_jwt_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_no_longer_has_a_hardcoded_default_secret() -> None:
    assert "jwt_secret_key" not in Settings.model_fields
    assert Settings.model_fields["jwt_access_secret_key"].is_required()
    assert Settings.model_fields["jwt_refresh_secret_key"].is_required()


def test_access_and_refresh_tokens_are_signed_with_different_keys() -> None:
    settings = make_settings()
    access_token = create_access_token("user-1", settings=settings)
    refresh_token = create_refresh_token("user-1", settings=settings)

    # An access token can't be decoded as a refresh token, and vice versa,
    # because the two are signed with different secrets.
    assert decode_token(access_token, TokenType.REFRESH, settings=settings) is None
    assert decode_token(refresh_token, TokenType.ACCESS, settings=settings) is None


def test_decode_token_rejects_wrong_token_type_even_with_shared_secret() -> None:
    # Regression test for the plan's explicit requirement: decode_token must
    # check the token_type claim before trusting either token, not rely on
    # key separation alone (e.g. if access/refresh secrets were ever
    # misconfigured to the same value).
    settings = make_settings(jwt_refresh_secret_key="access-secret")
    access_token = create_access_token("user-1", settings=settings)

    assert decode_token(access_token, TokenType.REFRESH, settings=settings) is None


def test_decode_token_accepts_matching_type() -> None:
    settings = make_settings()
    access_token = create_access_token("user-1", settings=settings)
    refresh_token = create_refresh_token("user-1", settings=settings)

    access_payload = decode_token(access_token, TokenType.ACCESS, settings=settings)
    refresh_payload = decode_token(refresh_token, TokenType.REFRESH, settings=settings)

    assert access_payload is not None
    assert access_payload.subject == "user-1"
    assert refresh_payload is not None
    assert refresh_payload.subject == "user-1"


def test_decode_token_rejects_garbage() -> None:
    settings = make_settings()
    assert decode_token("not-a-real-token", TokenType.ACCESS, settings=settings) is None
