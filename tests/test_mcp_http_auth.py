from __future__ import annotations

import pytest
from pydantic import AnyHttpUrl

from mcp.server.auth.provider import AccessToken
from gamota_research.mcp_server import (
    StaticBearerTokenVerifier,
    _http_auth_mode,
    _http_auth_settings,
)


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


def test_http_auth_settings_use_public_issuer_and_resource_url():
    verifier, settings = _http_auth_settings(
        "secret-token", "https://mcp.example.test/mcp"
    )

    assert isinstance(verifier, StaticBearerTokenVerifier)
    assert settings is not None
    assert settings.issuer_url == AnyHttpUrl("https://mcp.example.test")
    assert settings.resource_server_url == AnyHttpUrl("https://mcp.example.test/mcp")
    assert settings.required_scopes is None
    assert settings.validate_token_resource is True


def test_public_http_mode_requires_explicit_public_write_opt_in(monkeypatch):
    monkeypatch.setenv("GAMOTA_MCP_HTTP_AUTH", "none")
    monkeypatch.delenv("GAMOTA_MCP_PUBLIC_WRITES", raising=False)

    with pytest.raises(ValueError, match="GAMOTA_MCP_PUBLIC_WRITES=true"):
        _http_auth_mode()


def test_public_http_mode_is_available_after_explicit_opt_in(monkeypatch):
    monkeypatch.setenv("GAMOTA_MCP_HTTP_AUTH", "none")
    monkeypatch.setenv("GAMOTA_MCP_PUBLIC_WRITES", "true")

    assert _http_auth_mode() == "none"
