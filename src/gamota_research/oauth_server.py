from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from html import escape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pathlib import Path

from mcp.server.auth.routes import create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from .oauth_provider import GamotaOAuthProvider, OAUTH_SCOPES, OAuthStore


class _LoginRateLimiter:
    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, identity: str, now: float | None = None) -> bool:
        current = now if now is not None else time.monotonic()
        failures = self._failures[identity]
        while failures and failures[0] <= current - self.window_seconds:
            failures.popleft()
        return len(failures) < self.max_attempts

    def record_failure(self, identity: str, now: float | None = None) -> None:
        self._failures[identity].append(now if now is not None else time.monotonic())


def _secure_html(content: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        content,
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        },
    )


def _error_page(message: str, *, status_code: int) -> HTMLResponse:
    return _secure_html(
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Gamota Research authorization</title><main><h1>Authorization not completed</h1><p>{escape(message)}</p></main></html>",
        status_code=status_code,
    )


def _oauth_metadata(issuer: str) -> dict[str, object]:
    base = issuer.rstrip("/")
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "revocation_endpoint": f"{base}/revoke",
        "revocation_endpoint_auth_methods_supported": ["none"],
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": list(OAUTH_SCOPES),
        "client_id_metadata_document_supported": False,
        "authorization_response_iss_parameter_supported": False,
    }


def create_oauth_app(
    provider: GamotaOAuthProvider,
    store: OAuthStore,
    *,
    issuer: str,
) -> Starlette:
    issuer = str(AnyHttpUrl(issuer))
    issuer_origin = f"{urlsplit(issuer).scheme}://{urlsplit(issuer).netloc}"
    auth_routes = create_auth_routes(
        provider=provider,
        issuer_url=AnyHttpUrl(issuer),
        client_registration_options=ClientRegistrationOptions(
            enabled=False,
            valid_scopes=list(OAUTH_SCOPES),
            default_scopes=["research:read"],
        ),
    )
    routes = [route for route in auth_routes if getattr(route, "path", None) != "/.well-known/oauth-authorization-server"]
    limiter = _LoginRateLimiter()

    async def metadata(_request: Request) -> Response:
        return JSONResponse(
            _oauth_metadata(issuer),
            headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"},
        )

    async def login_page(request: Request) -> Response:
        ticket = request.query_params.get("ticket", "")
        login_request = store.get_login_request(ticket)
        if not login_request:
            return _error_page("This authorization request is invalid or expired. Restart the connection from ChatGPT.", status_code=400)
        csrf = secrets.token_urlsafe(32)
        if not store.set_login_csrf(ticket, csrf):
            return _error_page("This authorization request is invalid or expired.", status_code=400)
        scope_rows = []
        descriptions = {
            "research:read": "Read saved research runs, evidence, and reports.",
            "research:write": "Create and update research runs, sources, evidence, and claims.",
            "report:publish": "Publish a finalized report to the hosted report library.",
        }
        for scope in OAUTH_SCOPES:
            if scope in login_request["requested_scopes"]:
                scope_rows.append(
                    "<label><input type='checkbox' name='scope' value='"
                    + escape(scope, quote=True)
                    + "'><span><strong>"
                    + escape(scope)
                    + "</strong><br>"
                    + escape(descriptions[scope])
                    + "</span></label>"
                )
        body = (
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Connect Gamota Research</title><style>"
            "body{font:16px system-ui;background:#f5f7fb;color:#182230;margin:0;padding:32px}"
            "main{max-width:520px;margin:5vh auto;background:white;padding:32px;border:1px solid #dce3ec;border-radius:16px}"
            "h1{font-size:24px;margin:0 0 8px}p{color:#536273;line-height:1.5}"
            "label{display:flex;gap:12px;padding:14px 0;border-top:1px solid #e8edf2}"
            "input[type=password]{box-sizing:border-box;width:100%;padding:12px;border:1px solid #bbc7d4;border-radius:8px;margin:8px 0 20px}"
            "button{background:#155eef;color:white;border:0;border-radius:8px;padding:12px 16px;font-weight:650}"
            "</style><main><h1>Connect ChatGPT to Gamota Research</h1>"
            "<p>Authenticate with your owner credential, then choose exactly which research actions ChatGPT may use."
            " The credential is sent only to this HTTPS service and is never issued to ChatGPT.</p>"
            "<form method='post' action='/login'>"
            f"<input type='hidden' name='ticket' value='{escape(ticket, quote=True)}'>"
            f"<input type='hidden' name='csrf_token' value='{escape(csrf, quote=True)}'>"
            "<label for='owner_secret'>Owner credential</label>"
            "<input id='owner_secret' name='owner_secret' type='password' autocomplete='current-password' required>"
            "<h2>Permissions requested</h2>"
            + "".join(scope_rows)
            + "<button type='submit'>Approve selected permissions</button></form></main></html>"
        )
        return _secure_html(body)

    async def login_submit(request: Request) -> Response:
        form = await request.form()
        ticket = str(form.get("ticket", ""))
        csrf = str(form.get("csrf_token", ""))
        owner_secret = str(form.get("owner_secret", ""))
        scopes = [str(scope) for scope in form.getlist("scope")]
        login_request = store.get_login_request(ticket)
        if not login_request:
            return _error_page("This authorization request is invalid or expired.", status_code=400)
        origin = request.headers.get("origin")
        if origin != issuer_origin:
            return _error_page("The authorization form must be submitted from this service.", status_code=403)
        identity = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
        if not limiter.allowed(identity):
            return _error_page("Too many failed login attempts. Wait and restart the connection.", status_code=429)
        stored_csrf = login_request.get("csrf_hash")
        import hashlib

        if not stored_csrf or not secrets.compare_digest(
            stored_csrf, hashlib.sha256(csrf.encode("utf-8")).hexdigest()
        ):
            return _error_page("The security check failed. Reload the authorization page.", status_code=403)
        if not provider.verify_owner_secret(owner_secret):
            limiter.record_failure(identity)
            return _error_page("The credential was not accepted. Check it and try again.", status_code=401)
        approved = store.approve_login(
            ticket=ticket,
            csrf_token=csrf,
            scopes=scopes,
            subject="owner",
        )
        if approved is None:
            return _error_page("Select the read permission and only approve permissions shown above.", status_code=400)
        parsed = urlsplit(str(approved["redirect_uri"]))
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["code"] = str(approved["code"])
        if approved["state"] is not None:
            query["state"] = str(approved["state"])
        callback = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
        return RedirectResponse(callback, status_code=302, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})

    async def revoke_token(request: Request) -> Response:
        form = await request.form()
        client_id = str(form.get("client_id", ""))
        raw_token = str(form.get("token", ""))
        client = await provider.get_client(client_id)
        if client is not None and raw_token:
            access_token = await provider.load_access_token(raw_token)
            if access_token is not None and access_token.client_id == client.client_id:
                await provider.revoke_token(access_token)
        return Response(
            status_code=200,
            headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    routes.extend(
        [
            Route("/.well-known/oauth-authorization-server", metadata, methods=["GET"]),
            Route("/login", login_page, methods=["GET"]),
            Route("/login", login_submit, methods=["POST"]),
            Route("/revoke", revoke_token, methods=["POST"]),
        ]
    )
    return Starlette(debug=False, routes=routes)


def create_oauth_app_from_environment() -> Starlette:
    owner_secret = os.environ.get("GAMOTA_MCP_BEARER_TOKEN")
    issuer = os.environ.get("GAMOTA_OAUTH_ISSUER_URL")
    resource = os.environ.get("GAMOTA_PUBLIC_MCP_URL")
    redirect_uri = os.environ.get("GAMOTA_CHATGPT_REDIRECT_URI")
    store_path = os.environ.get("GAMOTA_OAUTH_DB")
    if not all((owner_secret, issuer, resource, redirect_uri, store_path)):
        raise ValueError(
            "GAMOTA_MCP_BEARER_TOKEN, GAMOTA_OAUTH_ISSUER_URL, "
            "GAMOTA_PUBLIC_MCP_URL, GAMOTA_CHATGPT_REDIRECT_URI, and GAMOTA_OAUTH_DB are required"
        )
    store = OAuthStore(Path(store_path).expanduser())
    provider = GamotaOAuthProvider(
        store,
        owner_secret=owner_secret,
        issuer=issuer,
        resource=resource,
        redirect_uri=redirect_uri,
    )
    return create_oauth_app(provider, store, issuer=issuer)


def main() -> None:
    import uvicorn

    uvicorn.run(
        create_oauth_app_from_environment(),
        host=os.environ.get("GAMOTA_OAUTH_HOST", "127.0.0.1"),
        port=int(os.environ.get("GAMOTA_OAUTH_PORT", "8001")),
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
        access_log=False,
    )


if __name__ == "__main__":
    main()
