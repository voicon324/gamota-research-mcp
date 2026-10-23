from __future__ import annotations

import base64
import hashlib
import re

from starlette.testclient import TestClient

from gamota_research.oauth_provider import GamotaOAuthProvider, OAuthStore
from gamota_research.oauth_server import create_oauth_app


ISSUER = "https://mcp.example.test/"
RESOURCE = "https://mcp.example.test/mcp"
CALLBACK = "https://chatgpt.com/connector/oauth/test-id"
CLIENT_ID = "gamota-chatgpt"


def _pkce_pair():
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge.rstrip(b"=").decode()


def _client(tmp_path):
    store = OAuthStore(tmp_path / "oauth.sqlite3")
    provider = GamotaOAuthProvider(
        store,
        owner_secret="owner-secret",
        issuer=ISSUER,
        resource=RESOURCE,
        redirect_uri=CALLBACK,
    )
    return TestClient(create_oauth_app(provider, store, issuer=ISSUER)), store


def test_oauth_metadata_advertises_only_supported_public_pkce_client(tmp_path):
    client, _ = _client(tmp_path)
    response = client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    metadata = response.json()
    assert metadata["issuer"] == ISSUER
    assert metadata["token_endpoint"] == f"{ISSUER.rstrip('/')}/token"
    assert metadata["code_challenge_methods_supported"] == ["S256"]
    assert metadata["token_endpoint_auth_methods_supported"] == ["none"]
    assert metadata["revocation_endpoint"] == f"{ISSUER.rstrip('/')}/revoke"
    assert metadata["revocation_endpoint_auth_methods_supported"] == ["none"]
    assert metadata["scopes_supported"] == ["research:read", "research:write", "report:publish"]
    assert "registration_endpoint" not in metadata
    assert metadata["authorization_response_iss_parameter_supported"] is False


def test_oauth_authorization_requires_owner_login_consent_and_pkce(tmp_path):
    client, store = _client(tmp_path)
    verifier, challenge = _pkce_pair()
    auth_response = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": CALLBACK,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "research:read research:write report:publish",
            "resource": RESOURCE,
            "state": "state-123",
        },
        follow_redirects=False,
    )
    assert auth_response.status_code == 302
    assert auth_response.headers["location"].startswith(f"{ISSUER.rstrip('/')}/login?ticket=")
    ticket = auth_response.headers["location"].split("ticket=", 1)[1]

    login_page = client.get(f"/login?ticket={ticket}")
    assert login_page.status_code == 200
    assert "form-action 'self' https://chatgpt.com" in login_page.headers["content-security-policy"]
    assert "report:publish" in login_page.text
    assert "name='owner_secret'" in login_page.text
    assert "owner-secret" not in login_page.text
    csrf = re.search(r"name='csrf_token' value='([^']+)'", login_page.text).group(1)

    failed = client.post(
        "/login",
        data={"ticket": ticket, "csrf_token": csrf, "owner_secret": "wrong", "scope": "research:read"},
        headers={"origin": ISSUER.rstrip("/")},
        follow_redirects=False,
    )
    assert failed.status_code == 401

    approved = client.post(
        "/login",
        data={
            "ticket": ticket,
            "csrf_token": csrf,
            "owner_secret": "owner-secret",
            "scope": ["research:read", "research:write", "report:publish"],
        },
        headers={"origin": ISSUER.rstrip("/")},
        follow_redirects=False,
    )
    assert approved.status_code == 303
    callback = approved.headers["location"]
    assert callback.startswith(CALLBACK + "?")
    assert "state=state-123" in callback
    code = callback.split("code=", 1)[1].split("&", 1)[0]
    assert store.get_authorization_code(code) is not None

    token_response = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": CALLBACK,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
            "resource": RESOURCE,
        },
    )
    assert token_response.status_code == 200, token_response.text
    token = token_response.json()["access_token"]
    assert token_response.json()["scope"] == "research:read research:write report:publish"
    assert store.get_access_token(token) is not None

    revoked = client.post(
        "/revoke",
        data={"token": token, "token_type_hint": "access_token", "client_id": CLIENT_ID},
    )
    assert revoked.status_code == 200, revoked.text
    assert store.get_access_token(token) is None

    wrong_pkce = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": CALLBACK,
            "client_id": CLIENT_ID,
            "code_verifier": "a" * 43,
            "resource": RESOURCE,
        },
    )
    assert wrong_pkce.status_code == 400
    assert wrong_pkce.json()["error"] == "invalid_grant"

    replay = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": CALLBACK,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
            "resource": RESOURCE,
        },
    )
    assert replay.status_code == 400
    assert replay.json()["error"] == "invalid_grant"


def test_oauth_login_rejects_csrf_and_wrong_callback(tmp_path):
    client, _ = _client(tmp_path)
    _, challenge = _pkce_pair()
    bad_callback = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": "https://attacker.example/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "research:read",
            "resource": RESOURCE,
        },
        follow_redirects=False,
    )
    assert bad_callback.status_code == 400

    authorized = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": CALLBACK,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "research:read",
            "resource": RESOURCE,
        },
        follow_redirects=False,
    )
    ticket = authorized.headers["location"].split("ticket=", 1)[1]
    page = client.get(f"/login?ticket={ticket}")
    csrf = re.search(r"name='csrf_token' value='([^']+)'", page.text).group(1)
    response = client.post(
        "/login",
        data={"ticket": ticket, "csrf_token": csrf + "x", "owner_secret": "owner-secret", "scope": "research:read"},
        headers={"origin": ISSUER.rstrip("/")},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_oauth_authorization_rejects_wrong_resource_and_unknown_scope(tmp_path):
    client, _ = _client(tmp_path)
    _, challenge = _pkce_pair()
    base = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": CALLBACK,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    wrong_resource = client.get(
        "/authorize",
        params={**base, "scope": "research:read", "resource": "https://other.example.test/mcp", "state": "bad-resource"},
        follow_redirects=False,
    )
    assert wrong_resource.status_code == 302
    assert "error=invalid_target" in wrong_resource.headers["location"]

    unknown_scope = client.get(
        "/authorize",
        params={**base, "scope": "research:read admin", "resource": RESOURCE, "state": "bad-scope"},
        follow_redirects=False,
    )
    assert unknown_scope.status_code == 302
    assert "error=invalid_scope" in unknown_scope.headers["location"]
