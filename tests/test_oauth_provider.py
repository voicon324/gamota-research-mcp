from __future__ import annotations

import pytest

from gamota_research.oauth_provider import OAuthAccessTokenVerifier, OAuthStore


@pytest.mark.anyio
async def test_oauth_access_tokens_are_resource_scoped_and_revocable(tmp_path):
    store = OAuthStore(tmp_path / "oauth.sqlite3")
    token = store.issue_access_token(
        client_id="gamota-chatgpt",
        scopes=["research:read"],
        resource="https://mcp.example.test/mcp",
        issuer="https://auth.example.test",
        subject="owner",
        expires_in=300,
    )
    verifier = OAuthAccessTokenVerifier(
        store,
        issuer="https://auth.example.test",
        resource="https://mcp.example.test/mcp",
    )

    accepted = await verifier.verify_token(token)
    assert accepted is not None
    assert accepted.client_id == "gamota-chatgpt"
    assert accepted.scopes == ["research:read"]
    assert accepted.resource == "https://mcp.example.test/mcp"
    assert accepted.claims == {"iss": "https://auth.example.test/"}

    wrong_resource = OAuthAccessTokenVerifier(
        store,
        issuer="https://auth.example.test",
        resource="https://other.example.test/mcp",
    )
    assert await wrong_resource.verify_token(token) is None

    store.revoke_access_token(token)
    assert await verifier.verify_token(token) is None


def test_oauth_tokens_expire_and_are_not_persisted_as_plaintext(tmp_path):
    path = tmp_path / "oauth.sqlite3"
    store = OAuthStore(path)
    token = store.issue_access_token(
        client_id="gamota-chatgpt",
        scopes=["research:read"],
        resource="https://mcp.example.test/mcp",
        issuer="https://auth.example.test",
        subject="owner",
        expires_in=-1,
    )

    assert store.get_access_token(token) is None
    raw_db = path.read_bytes()
    assert token.encode() not in raw_db


def test_oauth_authorization_codes_are_one_time_and_expire(tmp_path):
    store = OAuthStore(tmp_path / "oauth.sqlite3")
    code = store.issue_authorization_code(
        client_id="gamota-chatgpt",
        redirect_uri="https://chatgpt.com/connector/oauth/test",
        code_challenge="challenge",
        scopes=["research:read"],
        resource="https://mcp.example.test/mcp",
        subject="owner",
        expires_in=300,
    )

    assert store.consume_authorization_code(code) is not None
    assert store.consume_authorization_code(code) is None


def test_oauth_provider_only_accepts_the_fixed_chatgpt_client_and_scopes(tmp_path):
    from gamota_research.oauth_provider import GamotaOAuthProvider

    provider = GamotaOAuthProvider(
        OAuthStore(tmp_path / "oauth.sqlite3"),
        owner_secret="owner-secret",
        issuer="https://auth.example.test",
        resource="https://mcp.example.test/mcp",
        redirect_uri="https://chatgpt.com/connector/oauth/test",
    )

    assert provider.fixed_client_id == "gamota-chatgpt"
    assert provider.is_allowed_scope("research:read")
    assert not provider.is_allowed_scope("admin")
