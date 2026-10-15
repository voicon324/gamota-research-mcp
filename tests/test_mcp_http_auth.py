from __future__ import annotations

import pytest
from pydantic import AnyHttpUrl

from mcp.server.auth.provider import AccessToken
from gamota_research.mcp_server import StaticBearerTokenVerifier, _http_auth_settings


@pytest.mark.anyio
async def test_static_bearer_verifier_accepts_only_configured_token():
    verifier = StaticBearerTokenVerifier("secret-token", "https://mcp.example.test/mcp")

    accepted = await verifier.verify_token("secret-token")
    rejected = await verifier.verify_token("wrong-token")

    assert isinstance(accepted, AccessToken)
    assert accepted.client_id == "gamota-mission2"
    assert accepted.scopes == ["gamota:research"]
    assert accepted.resource == "https://mcp.example.test/mcp"
    assert rejected is None


def test_static_bearer_rejects_partial_credentials():
    with pytest.raises(ValueError, match="both"):
        _http_auth_settings("secret-token", None)
    with pytest.raises(ValueError, match="both"):
        _http_auth_settings(None, "https://mcp.example.test/mcp")


def test_http_auth_settings_use_resource_url_and_placeholder_issuer():
    verifier, settings = _http_auth_settings(
        "secret-token", "https://mcp.example.test/mcp"
    )

    assert isinstance(verifier, StaticBearerTokenVerifier)
    assert settings is not None
    assert settings.issuer_url == AnyHttpUrl("https://auth.example.com")
    assert settings.resource_server_url == AnyHttpUrl("https://mcp.example.test/mcp")
    assert settings.required_scopes == ["gamota:research"]
    assert settings.validate_token_resource is True
