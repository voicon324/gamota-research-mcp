from __future__ import annotations

from types import SimpleNamespace

import pytest

from mcp.server.auth.provider import AccessToken
from mcp.types import ListToolsResult, Tool

from gamota_research.oauth_auth import CompositeTokenVerifier, ToolScopeMiddleware


@pytest.mark.anyio
async def test_composite_verifier_preserves_legacy_permissions_and_accepts_oauth():
    class OAuthVerifier:
        async def verify_token(self, token):
            if token == "oauth-token":
                return AccessToken(
                    token=token,
                    client_id="gamota-chatgpt",
                    scopes=["research:read"],
                    resource="https://mcp.example.test/mcp",
                )
            return None

    verifier = CompositeTokenVerifier(
        "legacy-token", OAuthVerifier(), "https://mcp.example.test/mcp"
    )
    legacy = await verifier.verify_token("legacy-token")
    oauth = await verifier.verify_token("oauth-token")

    assert legacy is not None
    assert legacy.client_id == "gamota-mission2"
    assert legacy.scopes == ["gamota:research"]
    assert oauth is not None and oauth.client_id == "gamota-chatgpt"


@pytest.mark.anyio
async def test_scope_middleware_denies_publish_and_returns_oauth_challenge():
    token = AccessToken(
        token="read-only",
        client_id="gamota-chatgpt",
        scopes=["research:read"],
        resource="https://mcp.example.test/mcp",
    )
    request = SimpleNamespace(scope={"user": SimpleNamespace(access_token=token)})
    context = SimpleNamespace(
        method="tools/call",
        params={"name": "publish_game_decision_brief"},
        request=request,
    )
    called = False

    async def next_handler(_ctx):
        nonlocal called
        called = True
        return {"ok": True}

    result = await ToolScopeMiddleware(
        "https://mcp.example.test/.well-known/oauth-protected-resource/mcp"
    )(context, next_handler)

    assert not called
    assert result.is_error is True
    challenge = result.meta["mcp/www_authenticate"][0]
    assert "error=\"insufficient_scope\"" in challenge
    assert "resource_metadata=\"https://mcp.example.test/.well-known/oauth-protected-resource/mcp\"" in challenge


@pytest.mark.anyio
async def test_scope_middleware_publishes_openai_oauth_security_schemes():
    tool = Tool(name="publish_game_decision_brief", inputSchema={"type": "object"})
    context = SimpleNamespace(method="tools/list", params={}, request=None)

    async def next_handler(_ctx):
        return ListToolsResult(tools=[tool])

    result = await ToolScopeMiddleware(
        "https://mcp.example.test/.well-known/oauth-protected-resource/mcp"
    )(context, next_handler)

    assert result["tools"][0]["securitySchemes"] == [
        {"type": "oauth2", "scopes": ["report:publish"]}
    ]


@pytest.mark.anyio
async def test_scope_middleware_keeps_legacy_bearer_permissions():
    token = AccessToken(
        token="legacy",
        client_id="gamota-mission2",
        scopes=["gamota:research"],
        resource="https://mcp.example.test/mcp",
    )
    request = SimpleNamespace(scope={"user": SimpleNamespace(access_token=token)})
    context = SimpleNamespace(
        method="tools/call",
        params={"name": "publish_game_decision_brief"},
        request=request,
    )

    async def next_handler(_ctx):
        return {"published": True}

    result = await ToolScopeMiddleware(
        "https://mcp.example.test/.well-known/oauth-protected-resource/mcp"
    )(context, next_handler)
    assert result == {"published": True}
