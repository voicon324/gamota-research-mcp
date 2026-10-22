from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizeError,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl


OAUTH_SCOPES = ("research:read", "research:write", "report:publish")
ACCESS_TOKEN_TTL = 3600
AUTHORIZATION_CODE_TTL = 300
LOGIN_TICKET_TTL = 600


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class OAuthStore:
    """Persistent OAuth state; bearer tokens and codes are stored only by digest."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS oauth_login_requests (
                    ticket_hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    code_challenge TEXT NOT NULL,
                    state TEXT,
                    requested_scopes TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    csrf_hash TEXT,
                    expires_at INTEGER NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
                    code_hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    redirect_uri TEXT NOT NULL,
                    code_challenge TEXT NOT NULL,
                    state TEXT,
                    scopes TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS oauth_access_tokens (
                    token_hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    scopes TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    issuer TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def create_login_request(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        state: str | None,
        scopes: list[str],
        resource: str,
        expires_in: int = LOGIN_TICKET_TTL,
    ) -> str:
        ticket = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO oauth_login_requests
                   (ticket_hash, client_id, redirect_uri, code_challenge, state,
                    requested_scopes, resource, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _digest(ticket), client_id, redirect_uri, code_challenge, state,
                    json.dumps(scopes), resource, int(time.time()) + expires_in,
                ),
            )
        return ticket

    def set_login_csrf(self, ticket: str, csrf_token: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE oauth_login_requests SET csrf_hash = ?
                   WHERE ticket_hash = ? AND consumed = 0 AND expires_at >= ?""",
                (_digest(csrf_token), _digest(ticket), int(time.time())),
            )
        return cursor.rowcount == 1

    def get_login_request(self, ticket: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM oauth_login_requests
                   WHERE ticket_hash = ? AND consumed = 0 AND expires_at >= ?""",
                (_digest(ticket), int(time.time())),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["requested_scopes"] = json.loads(result["requested_scopes"])
        return result

    def approve_login(
        self,
        *,
        ticket: str,
        csrf_token: str,
        scopes: list[str],
        subject: str,
    ) -> dict[str, str | None] | None:
        now = int(time.time())
        code = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT * FROM oauth_login_requests
                   WHERE ticket_hash = ? AND consumed = 0 AND expires_at >= ?""",
                (_digest(ticket), now),
            ).fetchone()
            if (
                row is None
                or row["csrf_hash"] is None
                or not secrets.compare_digest(row["csrf_hash"], _digest(csrf_token))
            ):
                connection.rollback()
                return None
            requested_scopes = set(json.loads(row["requested_scopes"]))
            if not scopes or "research:read" not in scopes or not set(scopes).issubset(requested_scopes):
                connection.rollback()
                return None
            cursor = connection.execute(
                """UPDATE oauth_login_requests SET consumed = 1
                   WHERE ticket_hash = ? AND consumed = 0""",
                (_digest(ticket),),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None
            connection.execute(
                """INSERT INTO oauth_authorization_codes
                   (code_hash, client_id, redirect_uri, code_challenge, state,
                    scopes, resource, subject, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _digest(code), row["client_id"], row["redirect_uri"],
                    row["code_challenge"], row["state"], json.dumps(scopes),
                    row["resource"], subject, now + AUTHORIZATION_CODE_TTL,
                ),
            )
            connection.commit()
            return {"code": code, "state": row["state"], "redirect_uri": row["redirect_uri"]}

    def issue_authorization_code(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        scopes: list[str],
        resource: str,
        subject: str,
        expires_in: int = AUTHORIZATION_CODE_TTL,
    ) -> str:
        code = secrets.token_urlsafe(32)
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO oauth_authorization_codes
                   (code_hash, client_id, redirect_uri, code_challenge, scopes,
                    resource, subject, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _digest(code), client_id, redirect_uri, code_challenge,
                    json.dumps(scopes), resource, subject, int(time.time()) + expires_in,
                ),
            )
        return code

    def get_authorization_code(self, code: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM oauth_authorization_codes
                   WHERE code_hash = ? AND consumed = 0 AND expires_at >= ?""",
                (_digest(code), int(time.time())),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["scopes"] = json.loads(result["scopes"])
        return result

    def consume_authorization_code(self, code: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT * FROM oauth_authorization_codes
                   WHERE code_hash = ? AND consumed = 0 AND expires_at >= ?""",
                (_digest(code), int(time.time())),
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            cursor = connection.execute(
                "UPDATE oauth_authorization_codes SET consumed = 1 WHERE code_hash = ? AND consumed = 0",
                (_digest(code),),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None
            connection.commit()
        result = dict(row)
        result["scopes"] = json.loads(result["scopes"])
        return result

    def issue_access_token(
        self,
        *,
        client_id: str,
        scopes: list[str],
        resource: str,
        issuer: str,
        subject: str,
        expires_in: int = ACCESS_TOKEN_TTL,
    ) -> str:
        token = secrets.token_urlsafe(32)
        issuer = str(AnyHttpUrl(issuer))
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO oauth_access_tokens
                   (token_hash, client_id, scopes, resource, issuer, subject, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    _digest(token), client_id, json.dumps(scopes), resource, issuer,
                    subject, int(time.time()) + expires_in,
                ),
            )
        return token

    def get_access_token(self, token: str) -> AccessToken | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT * FROM oauth_access_tokens
                   WHERE token_hash = ? AND revoked = 0 AND expires_at >= ?""",
                (_digest(token), int(time.time())),
            ).fetchone()
        if row is None:
            return None
        return AccessToken(
            token=token,
            client_id=row["client_id"],
            scopes=json.loads(row["scopes"]),
            resource=row["resource"],
            expires_at=row["expires_at"],
            subject=row["subject"],
            claims={"iss": row["issuer"]},
        )

    def revoke_access_token(self, token: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE oauth_access_tokens SET revoked = 1 WHERE token_hash = ?",
                (_digest(token),),
            )


class OAuthAccessTokenVerifier:
    def __init__(self, store: OAuthStore, *, issuer: str, resource: str) -> None:
        self.store = store
        self.issuer = str(AnyHttpUrl(issuer))
        self.resource = resource

    async def verify_token(self, token: str) -> AccessToken | None:
        access = self.store.get_access_token(token)
        if access is None or access.resource != self.resource:
            return None
        if (access.claims or {}).get("iss") != self.issuer:
            return None
        return access


class GamotaOAuthProvider(OAuthAuthorizationServerProvider[Any, Any, Any]):
    fixed_client_id = "gamota-chatgpt"

    def __init__(
        self,
        store: OAuthStore,
        *,
        owner_secret: str,
        issuer: str,
        resource: str,
        redirect_uri: str,
    ) -> None:
        self.store = store
        self.owner_secret = owner_secret
        self.issuer = str(AnyHttpUrl(issuer))
        self.resource = resource
        self.redirect_uri = redirect_uri

    def is_allowed_scope(self, scope: str) -> bool:
        return scope in OAUTH_SCOPES

    def verify_owner_secret(self, candidate: str) -> bool:
        return secrets.compare_digest(
            candidate.encode("utf-8"), self.owner_secret.encode("utf-8")
        )

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        if client_id != self.fixed_client_id:
            return None
        return OAuthClientInformationFull.model_validate(
            {
                "client_id": self.fixed_client_id,
                "redirect_uris": [self.redirect_uri],
                "response_types": ["code"],
                "grant_types": ["authorization_code"],
                "token_endpoint_auth_method": "none",
                "scope": " ".join(OAUTH_SCOPES),
                "client_name": "ChatGPT Gamota Research",
            }
        )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        raise NotImplementedError("Only the preconfigured ChatGPT OAuth client is allowed")

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        if str(params.redirect_uri) != self.redirect_uri:
            raise AuthorizeError("invalid_request", "Unapproved redirect URI")
        if params.resource != self.resource:
            raise AuthorizeError("invalid_target", "Unknown MCP resource")
        scopes = params.scopes or list(OAUTH_SCOPES)
        if not scopes or any(not self.is_allowed_scope(scope) for scope in scopes):
            raise AuthorizeError("invalid_scope", "Requested scope is not supported")
        ticket = self.store.create_login_request(
            client_id=client.client_id,
            redirect_uri=str(params.redirect_uri),
            code_challenge=params.code_challenge,
            state=params.state,
            scopes=scopes,
            resource=self.resource,
        )
        return f"{self.issuer.rstrip('/')}/login?{urlencode({'ticket': ticket})}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        row = self.store.get_authorization_code(authorization_code)
        if row is None or row["client_id"] != client.client_id:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=row["scopes"],
            expires_at=row["expires_at"],
            client_id=row["client_id"],
            code_challenge=row["code_challenge"],
            redirect_uri=row["redirect_uri"],
            redirect_uri_provided_explicitly=True,
            resource=row["resource"],
            subject=row["subject"],
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        row = self.store.consume_authorization_code(authorization_code.code)
        if row is None or row["client_id"] != client.client_id:
            raise TokenError("invalid_grant", "Authorization code is invalid or already used")
        token = self.store.issue_access_token(
            client_id=client.client_id,
            scopes=row["scopes"],
            resource=row["resource"],
            issuer=self.issuer,
            subject=row["subject"],
        )
        return OAuthToken(
            access_token=token,
            expires_in=ACCESS_TOKEN_TTL,
            scope=" ".join(row["scopes"]),
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        raise TokenError("unsupported_grant_type", "Refresh tokens are not issued")

    async def load_access_token(self, token: str) -> AccessToken | None:
        access = self.store.get_access_token(token)
        if access is None or access.resource != self.resource:
            return None
        if (access.claims or {}).get("iss") != self.issuer:
            return None
        return access

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self.store.revoke_access_token(token.token)
