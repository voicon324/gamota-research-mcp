from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient
from mcp.server.transport_security import TransportSecuritySettings

from gamota_research.domain.fixture_provider import FixtureStoreProvider
from gamota_research.domain.store_service import StoreService
from gamota_research.mcp_server import create_mcp_server
from gamota_research.oauth_provider import OAuthAccessTokenVerifier, OAuthStore
from gamota_research.service import ResearchService


RESOURCE = "https://mcp.example.test/mcp"
ISSUER = "https://mcp.example.test/"


def _headers(token: str | None = None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _initialize(client: TestClient, token: str):
    return client.post(
        "/mcp",
        headers=_headers(token),
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "oauth-integration-test", "version": "1.0"},
            },
        },
    )


def test_mcp_http_keeps_bearer_and_enforces_oauth_scopes(repository, tmp_path):
    store = OAuthStore(tmp_path / "oauth.sqlite3")
    read_token = store.issue_access_token(
        client_id="gamota-chatgpt",
        scopes=["research:read"],
        resource=RESOURCE,
        issuer=ISSUER,
        subject="owner",
    )
    verifier = OAuthAccessTokenVerifier(store, issuer=ISSUER, resource=RESOURCE)
    server = create_mcp_server(
        ResearchService(repository),
        StoreService(
            repository,
            FixtureStoreProvider(Path(__file__).parent / "fixtures" / "store_fixture.json"),
        ),
        http_bearer_token="legacy-bearer",
        public_mcp_url=RESOURCE,
        oauth_verifier=verifier,
        oauth_issuer_url=ISSUER,
    )
    app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    with TestClient(app, base_url="http://localhost") as client:
        metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200
        assert metadata.json()["resource"] == RESOURCE
        assert metadata.json()["authorization_servers"] == [ISSUER]

        unauthenticated = client.post(
            "/mcp",
            headers=_headers(),
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert unauthenticated.status_code == 401
        assert "resource_metadata=" in unauthenticated.headers["www-authenticate"]

        initialized = _initialize(client, read_token)
        assert initialized.status_code == 200, initialized.text

        listed = client.post(
            "/mcp",
            headers=_headers(read_token),
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert listed.status_code == 200, listed.text
        tools = listed.json()["result"]["tools"]
        assert len(tools) == 18
        publish = next(tool for tool in tools if tool["name"] == "publish_game_decision_brief")
        assert publish["securitySchemes"] == [{"type": "oauth2", "scopes": ["report:publish"]}]

        denied = client.post(
            "/mcp",
            headers=_headers(read_token),
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "publish_game_decision_brief", "arguments": {}},
            },
        )
        assert denied.status_code == 200, denied.text
        result = denied.json()["result"]
        assert result["isError"] is True
        assert "insufficient_scope" in result["_meta"]["mcp/www_authenticate"][0]

        write_denied = client.post(
            "/mcp",
            headers=_headers(read_token),
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "create_research_run", "arguments": {"question": "test"}},
            },
        )
        assert write_denied.json()["result"]["isError"] is True

        legacy = _initialize(client, "legacy-bearer")
        assert legacy.status_code == 200, legacy.text
        legacy_tools = client.post(
            "/mcp",
            headers=_headers("legacy-bearer"),
            json={"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
        )
        assert len(legacy_tools.json()["result"]["tools"]) == 18
