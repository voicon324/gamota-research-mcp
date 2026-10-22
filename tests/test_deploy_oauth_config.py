from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_oauth_nginx_routes_bypass_spa_and_use_loopback_services():
    config = (ROOT / "deploy" / "nginx-oauth-locations.conf").read_text()
    expected = {
        "/.well-known/oauth-protected-resource/mcp": 8000,
        "/.well-known/oauth-authorization-server": 8001,
        "/authorize": 8001,
        "/token": 8001,
        "/revoke": 8001,
        "/login": 8001,
    }
    for route, port in expected.items():
        assert f"location = {route} {{" in config
        assert f"proxy_pass http://127.0.0.1:{port}{route};" in config
    assert "proxy_set_header Authorization $http_authorization;" in config
    assert "try_files" not in config


def test_oauth_service_is_loopback_only_and_database_is_persistent():
    service = (ROOT / "deploy" / "gamota-research-oauth.service").read_text()
    env = (ROOT / "deploy" / "env.example").read_text()
    assert "-m gamota_research.oauth_server" in service
    assert "ReadWritePaths=/var/lib/gamota-research-mcp" in service
    assert "GAMOTA_OAUTH_HOST=127.0.0.1" in env
    assert "GAMOTA_OAUTH_PORT=8001" in env
    assert "GAMOTA_OAUTH_DB=/var/lib/gamota-research-mcp/oauth.sqlite3" in env


def test_public_oauth_verifier_uses_trusted_tls_without_secrets():
    script = (ROOT / "deploy" / "verify-oauth.sh").read_text()
    assert "curl -k" not in script
    assert "GAMOTA_MCP_BEARER_TOKEN" not in script
    assert "resource_metadata=" in script
    assert "code_challenge_methods_supported" in script
