# ChatGPT MCP OAuth design

## Outcome

Connect ChatGPT Web to the hosted Gamota Research MCP so a normal ChatGPT research conversation can combine native web search with Gamota's evidence, validation, and report tools. Keep existing Codex/Claude static-bearer clients working unchanged.

## Observed baseline

- MCP resource: `https://52.64.163.35/mcp`; unauthenticated requests correctly receive `401`.
- The public IP has a valid trusted TLS certificate (`curl` verification succeeds).
- MCP SDK is pinned at `mcp==2.3.0`; it currently uses `StaticBearerTokenVerifier` and placeholder issuer `https://auth.example.com`.
- Public well-known paths currently fall through to the React SPA. This is why ChatGPT OAuth auto-discovery fails.
- The service exposes 18 tools, including data writes and report publishing.
- The ChatGPT connector draft shows callback `https://chatgpt.com/connector/oauth/nIrt-FeijEVZ`; configuration must use the exact callback shown in the active connector form.

## Architecture

1. Preserve the current bearer credential and its current tool permissions for existing clients. Add a composite verifier that recognizes either that exact legacy credential or a separately issued OAuth access token. OAuth tokens never inherit the legacy bearer credential or unrestricted legacy authority.
2. Add a logically separate authorization-server ASGI service, routed by Nginx on the existing trusted HTTPS origin. Use the maintained MCP Python SDK OAuth authorization handlers/provider contracts for authorization code, PKCE S256, token exchange, resource indicators, and expiry. Persist one-time authorization codes and short-lived access/refresh tokens in a dedicated SQLite file under the existing persistent service data directory.
3. Use a fixed public client (`gamota-chatgpt`) for the current ChatGPT connector form. Allow only the exact callback URI shown by that form. Advertise `token_endpoint_auth_methods_supported: ["none"]`; do not advertise CIMD, DCR, or RFC 9207 issuer support unless those protocols are implemented and verified. Accept only authorization-code + PKCE S256. Reject unknown client IDs, callback URIs, scopes, resources, and replayed/expired codes.
4. The owner login page asks for the existing bearer secret over HTTPS and shows the requested scopes for explicit consent. Compare the secret in constant time, rate-limit failed attempts, protect form submission from CSRF, never log/store/return the secret, and issue an independent random OAuth token. This is a temporary single-owner bridge; later replace it with a dedicated login identity.
5. Use three server-enforced scopes: `research:read`, `research:write`, and `report:publish`. OAuth tool calls are authorized by the scope required by that tool. The legacy bearer retains the full permissions it already had. ChatGPT tool annotations and consent are UX aids, not the permission boundary.
6. Keep the MCP server a resource server using `TokenVerifier`/`AuthSettings`; route Protected Resource Metadata to the MCP service and Authorization Server Metadata plus `/authorize`, `/token`, and login/consent endpoints to the authorization service. Nginx only terminates TLS and routes; it does not implement OAuth. The UI root, reports, `/mcp`, and current proxy streaming behavior remain intact.
7. Start with a read-only ChatGPT connection. After verified MCP initialization/tool discovery, grant write and publish scopes only for the requested demo research run. Create and publish one actual report via ChatGPT MCP tools, then capture redacted before/after UI and conversation evidence for the Mission 3 video.

## Security and compatibility requirements

- Never place the legacy bearer in OAuth URLs, redirect URLs, cookies, browser storage, logs, OAuth access tokens, or MCP results.
- Access tokens are random, short-lived, resource-bound to `https://52.64.163.35/mcp`, persisted only as a one-way digest, and revocable. Refresh-token rotation/revocation is persisted; do not issue a token if persistence fails.
- Authorization codes are one-time, short-lived, client/redirect/resource-bound, and PKCE-bound. Validate state round-trip. Use exact string allowlists for client ID, resource, and redirect URI.
- CSRF protection, secure HttpOnly SameSite cookies, no-store responses, same-origin form submission, and login rate limiting are required.
- The 401 challenge points to `https://52.64.163.35/.well-known/oauth-protected-resource/mcp`; metadata is JSON and the advertised issuer is exactly `https://52.64.163.35/` (including trailing slash).
- Legacy bearer requests continue to return the same 18 tools and preserve their existing behavior. Missing, invalid, expired, revoked, wrong-resource, and insufficient-scope OAuth requests fail closed.
- No no-auth MCP mode is introduced. Existing bearer clients do not need OAuth registration or token exchange.

## Verification

1. Unit tests for legacy token compatibility, OAuth token persistence/expiry/revocation/resource/scope validation, scope denial by tool, exact redirect/client/resource allowlists, login-secret rejection and acceptance, constant-time verification call, CSRF, PKCE mismatch, code replay, and OAuth metadata.
2. Run the existing full suite and new auth tests. Run the actual existing bearer deployment verification before and after release.
3. Check public TLS without `curl -k`; check both metadata routes return JSON; inspect the unauthenticated MCP 401 challenge; complete an end-to-end OAuth authorization/code/token flow with a PKCE test client; verify read-only cannot write/publish; verify legacy bearer still discovers all 18 tools.
4. Connect ChatGPT Web through the active connector form, verify OAuth login, actual tool listing, then use native web search plus MCP tools to save sources/evidence/claims, validate, and publish a real report. Confirm it appears in the hosted report UI.
5. Deploy only after local verification and prepare a service/Nginx rollback that preserves the database, reports, and legacy bearer route.

## Limits

The bridge uses the existing shared bearer to authenticate the sole owner. It is a practical first connection for this single-owner demo but creates shared-secret reuse risk; rotate to a separate OAuth login credential or identity provider before broad user access. The IP origin is currently trusted TLS, but a stable DNS name remains preferable for a long-lived public product.
