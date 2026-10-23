from __future__ import annotations

from mcp.server.transport_security import TransportSecuritySettings
from starlette.testclient import TestClient

from gamota_research.mcp_server import create_mcp_server
from gamota_research.service import ResearchService


def test_public_mcp_allows_anonymous_write_and_publish_tools(repository):
    server = create_mcp_server(ResearchService(repository))
    app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
    }

    with TestClient(app, base_url="http://localhost") as client:
        initialized = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "public-mcp-test", "version": "1.0"},
                },
            },
        )
        assert initialized.status_code == 200, initialized.text

        listed = client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert listed.status_code == 200, listed.text
        tool_names = {item["name"] for item in listed.json()["result"]["tools"]}
        assert "create_research_run" in tool_names
        assert "publish_game_decision_brief" in tool_names

        created = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "create_research_run",
                    "arguments": {"question": "Anonymous public MCP smoke"},
                },
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["result"]["isError"] is False


def test_public_mcp_allows_configured_frontend_origin(monkeypatch, repository):
    from gamota_research import mcp_server

    monkeypatch.setenv(
        "GAMOTA_MCP_ALLOWED_ORIGINS",
        "https://52-64-163-35.sslip.io",
    )
    settings_factory = getattr(mcp_server, "_http_transport_security_settings", None)
    assert callable(settings_factory), "HTTP transport does not configure explicit frontend origins"

    server = create_mcp_server(ResearchService(repository))
    app = server.streamable_http_app(
        json_response=True,
        stateless_http=True,
        transport_security=settings_factory(),
    )
    headers = {
        "Origin": "https://52-64-163-35.sslip.io",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-03-26",
    }

    with TestClient(app, base_url="http://127.0.0.1:8002") as client:
        response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "frontend-origin-test", "version": "1.0"},
                },
            },
        )

    assert response.status_code == 200, response.text
