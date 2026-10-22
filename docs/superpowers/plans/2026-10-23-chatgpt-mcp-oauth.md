# ChatGPT MCP OAuth Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Connect ChatGPT Web to Gamota Research MCP using OAuth 2.1 + PKCE while preserving the existing bearer clients and enforcing per-tool permissions.

**Architecture:** A dedicated Starlette authorization service uses the MCP Python SDK's OAuth provider/handlers and a persistent SQLite store. The existing MCP service remains the resource server with a composite token verifier and middleware that enforces tool scopes. Nginx routes public metadata and OAuth paths to the correct local service while preserving `/mcp` and the UI.

**Tech Stack:** Python 3.13, pinned `mcp==2.3.0`, Starlette, SQLite, Nginx, pytest.

**Spec:** `docs/chatgpt-mcp-oauth-design.md`

## Global Constraints

- Preserve existing bearer value, `/mcp` URL, MCP tool names/schemas, and existing authorized behavior.
- OAuth tokens are resource-bound to `https://52.64.163.35/mcp`; only authorization-code + PKCE S256 is accepted.
- OAuth scopes are exactly `research:read`, `research:write`, and `report:publish`.
- The only OAuth client ID is `gamota-chatgpt`; only the exact URI from the active ChatGPT form is accepted.
- Never log, output, commit, store, or forward the bearer login secret.
- Do not expose MCP without auth; do not change research DB/report data or frontend URLs.

## Review Focus

- A missing/malformed `resource` or callback must be rejected before issuing a code.
- An OAuth token for another issuer/resource or an expired/revoked token must fail authentication.
- A token missing write/publish scopes must be denied by the tool handler, not merely hidden in ChatGPT.
- Restart must preserve active OAuth token/code-consumption/revocation state as applicable.
- Existing static bearer behavior must remain byte-for-byte compatible and continue listing 18 tools.

### Task 1: Persistent OAuth provider and login consent

**Files:**
- Create `src/gamota_research/oauth_provider.py`
- Create `src/gamota_research/oauth_store.py`
- Create `tests/test_oauth_provider.py`

**Interfaces:**
- `OAuthStore(path: Path)` creates its own schema and exposes atomic code/token save, one-time consume, lookup, rotate, and revoke methods.
- `GamotaOAuthProvider(store, owner_secret, issuer_url, resource_url, redirect_uri)` implements the SDK `OAuthAuthorizationServerProvider` contract for the fixed public client.
- `OAuthAccessTokenVerifier(store, expected_issuer, expected_resource)` returns SDK `AccessToken` only for active, unexpired, resource-bound tokens.

- [ ] Write tests for valid/invalid fixed client, scope list, authorization-code expiry, one-time consume, wrong PKCE verifier, resource mismatch, token expiry, revocation, and wrong issuer/resource.
- [ ] Run `uv run pytest tests/test_oauth_provider.py -v`; verify missing interfaces fail with the intended assertions.
- [ ] Implement SQLite persistence and provider methods using SDK `AuthorizationCode`, `RefreshToken`, `AccessToken`, and `OAuthToken` types.
- [ ] Re-run the focused tests; verify codes are consumed atomically and tokens persist across store re-open.

### Task 2: MCP composite auth and tool scope enforcement

**Files:**
- Modify `src/gamota_research/mcp_server.py`
- Modify `src/gamota_research/mcp_tools.py`
- Create `tests/test_mcp_oauth_scopes.py`
- Modify `tests/test_mcp_http_auth.py`

**Interfaces:**
- `CompositeTokenVerifier(legacy_token, oauth_verifier, resource_url)` accepts the current bearer as `research:read research:write report:publish` under the existing client identity; otherwise delegates to OAuth verification.
- `ToolScopeMiddleware` checks `tools/call` against a fixed map: getters/list/read tools → `research:read`; run/source/evidence/claim/issue/finalize/progress writes → `research:write`; report publication → `report:publish`.

- [ ] Write tests for old bearer acceptance unchanged, OAuth read access, denied write without scope, denied publish without scope, and unknown tool policy denial.
- [ ] Run new tests and existing `tests/test_mcp_http_auth.py`; verify tests fail because composite and scope guard are absent.
- [ ] Implement verifier selection and server middleware; retain exact existing static bearer token configuration.
- [ ] Run new tests, MCP protocol tests, and HTTP auth tests.

### Task 3: Authorization server ASGI routes and OAuth metadata

**Files:**
- Create `src/gamota_research/oauth_server.py`
- Create `tests/test_oauth_http.py`
- Modify `pyproject.toml` and `uv.lock` only if a runtime dependency is required.

**Interfaces:**
- `create_oauth_app(provider, *, issuer_url, resource_url, redirect_uri)` returns a Starlette ASGI app exposing JSON OAuth metadata, `/authorize`, `/token`, `/login`, and `/consent`.
- OAuth metadata advertises `code_challenge_methods_supported: ["S256"]`, `token_endpoint_auth_methods_supported: ["none"]`, and no DCR/CIMD/RFC9207 claims.

- [ ] Write HTTP tests for metadata JSON, absent/wrong login secret, missing/incorrect CSRF, exact callback allowlist, rejected unknown scope/client/resource, successful login+consent redirect, token exchange with PKCE, and replay rejection.
- [ ] Run focused tests and verify expected failures before implementation.
- [ ] Add rate limiting, no-store headers, secure same-site HttpOnly session/CSRF handling, HTML-escaped scope consent, and owner-secret comparison without logging.
- [ ] Run HTTP tests and inspect logs/output for secret leakage.

### Task 4: Deployment wiring and documentation

**Files:**
- Create `deploy/gamota-oauth.service`
- Modify `deploy/README_DEPLOY.md`, `deploy/env.example`, and the documented Nginx snippet
- Create or extend `deploy/verify-oauth.sh`
- Create `tests/test_deploy_oauth_config.py`

**Interfaces:**
- OAuth AS binds to loopback port `8001`; its DB uses `GAMOTA_OAUTH_DB` in the existing persistent data directory.
- Nginx routes `/.well-known/oauth-authorization-server`, `/authorize`, `/token`, `/login`, and `/consent` to port 8001; protected-resource metadata and `/mcp` continue to the MCP service on 8000.

- [ ] Write tests that assert route destinations, TLS host issuer/resource values, no SPA fallback for OAuth metadata, and existing `/mcp`/UI/report locations preserved.
- [ ] Run focused deployment-config tests and confirm failure for the current missing OAuth routes.
- [ ] Implement a separate systemd unit and Nginx location changes with exact prior config backup, `nginx -t`, reload, and rollback instructions.
- [ ] Run all repository tests; run deployment bundle checks and verify shell commands never print environment variables.

### Task 5: ChatGPT connection, actual research run, and video evidence

**Files:**
- Update `docs/mission3-deployment-verification.md`
- Create `evidence/mission3/chatgpt-oauth/` screenshots and sanitized trace
- Update video project/voiceover deliverables outside the repo as needed.

- [ ] Verify TLS and public metadata routes without `-k`; check 401 includes correct `resource_metadata` challenge.
- [ ] Verify existing bearer initialization and all 18 tools, then complete MCP Inspector authorization and test read/write scope denial.
- [ ] Use the exact live callback in ChatGPT connector configuration; connect through OAuth and call read-only tools first.
- [ ] Run one real market research session using ChatGPT native search plus Gamota MCP, save evidence and claims, finalize, and publish the report.
- [ ] Confirm the report is visible from the hosted UI and capture redacted evidence for the Mission 3 video.
- [ ] Re-run full tests and `deploy/verify.sh`; document actual results and rollback target.
