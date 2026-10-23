# AITC server deployment and operations

This bundle enables Streamable HTTP while preserving stdio. It also documents the current hosted deployment and retains the installation, verification and rollback procedure for future operations.

## Current deployment status (2026-10-15)

- Public MCP endpoint: `https://52-64-163-35.sslip.io/mcp` (bearer authentication required).
- Public unauthenticated MCP endpoint: `https://52-64-163-35.sslip.io/mcp-public` (all tools, including write and publish, are exposed without authentication at the owner's request).
- The systemd application service and Nginx reverse proxy are active; the application binds to loopback behind Nginx.
- TLS is valid on the `52-64-163-35.sslip.io` hostname. The raw IP does not match the certificate hostname.
- The original deployment baseline had 15 tools. After the MVP report pipeline release on 2026-10-15, public checks report unauthenticated `/mcp` `401`, authenticated initialize `PASS`, and authenticated discovery `18 tools`.
- The deployed checkout was read-only verified at revision `415e59513596fabd375cff2fbcc73817eb23375a` before the MVP release. Service and Nginx remain active.
- The bearer value, private key, environment contents and Authorization headers are intentionally omitted. See [`../docs/mission2-deployment-verification.md`](../docs/mission2-deployment-verification.md) for sanitized evidence.

## Confirmed contract

- Target: the AITC server identified by the owner; owner reports server setup is ready.
- Application: `gamota-research-mcp`; Streamable HTTP at `/mcp`.
- Production executor: human operator.
- Authentication: static pre-shared bearer token; missing/wrong token is rejected.
- Existing stdio transport remains the default.
- Research DB: separate persistent SQLite file, not a temporary smoke DB.

## Verify at G4 before installation

Record actual values in the operator's secure deployment notes (do not commit secrets): install directory, service user, persistent SQLite path, public MCP URL, ingress/proxy vs direct port, reserved port, service manager, TLS termination, and firewall/security-group state. The application defaults to binding `127.0.0.1`; expose it only through the approved TLS ingress. If a direct listener is required, set host/port only after confirming the firewall and TLS plan.

## Configuration

Create a root-readable environment file from `env.example` on the server and set:

- `GAMOTA_TRANSPORT=streamable-http`
- `GAMOTA_MCP_BEARER_TOKEN` to a newly generated high-entropy secret, delivered through the approved secret channel
- `GAMOTA_PUBLIC_MCP_URL` to the final HTTPS MCP endpoint ending in `/mcp`
- `GAMOTA_RESEARCH_DB` to the persistent database path
- `GAMOTA_REPORTS_DIR=/var/lib/gamota-research-mcp/published-reports` for immutable public report artifacts
- `GAMOTA_PUBLIC_SITE_URL=https://<public-host>` so MCP returns a direct report-page link
- `GAMOTA_HOST` to `127.0.0.1` behind a reverse proxy (default)
- `PORT` to the locally reserved application port
- `GAMOTA_STORE_PROVIDER=fixture` for deterministic demo data, or explicitly choose `apple_rss` if live Apple Vietnam Top Free/Top Paid data is desired

Do not copy a development `.env`, SQLite DB, key, or bearer token into this bundle or Git. Do not pass the token as a command-line argument. Protect the environment file with owner-only read permissions.

### Public ChatGPT MCP and legacy bearer authentication

The original `/mcp` endpoint continues to require the existing bearer token for Codex/Claude and other configured clients. ChatGPT uses `/mcp-public`, proxied to a second loopback MCP service on port `8002`. That endpoint exposes every tool, including create/update/publish, to any caller that can reach the public HTTPS host. Treat it as a public write API; do not use it for private research or confidential source material. The OAuth endpoints remain available but are not used by `/mcp-public`.

Set these values in the protected server environment file:

- `GAMOTA_OAUTH_DB=/var/lib/gamota-research-mcp/oauth.sqlite3`
- `GAMOTA_OAUTH_ISSUER_URL=https://<public-host>/` (canonical issuer, including the trailing slash)
- `GAMOTA_CHATGPT_REDIRECT_URI` to the exact callback displayed in the active ChatGPT connector form
- `GAMOTA_OAUTH_HOST=127.0.0.1` and `GAMOTA_OAUTH_PORT=8001`

The OAuth login uses `GAMOTA_MCP_BEARER_TOKEN` as the temporary single-owner login credential. The credential is compared in constant time, never stored by the OAuth service, and never sent to ChatGPT. The login page requires explicit scope selection. OAuth scopes are `research:read`, `research:write`, and `report:publish`; every MCP tool call is checked server-side. Do not use this shared-credential bridge for multiple users; replace it with a dedicated identity provider before broad access.

Install `gamota-research-oauth.service` and [`gamota-research-mcp-public.service`](gamota-research-mcp-public.service). Include [`nginx-oauth-locations.conf`](nginx-oauth-locations.conf) inside the existing HTTPS server block before the SPA fallback. Keep the current `/mcp`, UI, report, certificate, and port 80 locations intact.

## Install and operate

1. Review the repository revision and deployment files, then transfer the approved source/bundle using the server skill.
2. Install Python 3.13 and `uv` if not already present; create the service environment and run `uv sync --frozen --no-dev` from the install directory.
3. Create the persistent DB parent directory and `/var/lib/gamota-research-mcp/published-reports` owned by the service user, readable by Nginx, and writable by the service. Set up the environment file as described above.
4. Adapt `gamota-research-mcp.service` and `gamota-research-oauth.service` to the verified paths, service identity, and ports. Both units need the existing persistent-data directory in `ReadWritePaths`.
5. Configure the approved TLS ingress for `/mcp` and OAuth routes using the reviewed Nginx snippet. Keep Authorization headers and owner credentials out of proxy logs and diagnostic output.
6. Run `verify.sh` with the public URL and token supplied through a protected environment, then run `verify-oauth.sh` without `curl -k`. Confirm bearer initialization, the 18-tool manifest, JSON discovery metadata, and a 401 challenge that advertises the Protected Resource Metadata URL.
7. Complete the browser OAuth flow with the exact ChatGPT callback. Verify a read-only token cannot write or publish before granting those scopes for a specific research run.
8. Capture only nonsecret evidence: both services active, loopback listeners, public URL, metadata JSON, unauthenticated `401`, legacy bearer initialize and tool discovery, and ChatGPT OAuth tool discovery. Never capture an Authorization header or token.

## Rollback

Stop and disable the service, restore the previous ingress route/configuration, and restore the prior application release. Keep the research database intact unless the owner separately approves a data migration/retention action. Rotate the bearer token if it may have been exposed. `rollback.sh` only stops/disables this service; the operator must verify the unit name before running it.

## Verification helper

`verify.sh` uses curl and Python's MCP client. Set `MCP_URL` and `GAMOTA_MCP_BEARER_TOKEN` in the protected shell environment, then execute the script. It prints status and tool count, never the token. A successful result is not evidence of public availability until run from the intended network path.

## Static research UI

The evaluator-facing website is a static React/Vite build. Nginx serves it at `/`; the authenticated Python service remains at `/mcp`. Published reports are static JSON/Markdown files written by the MCP process into `/var/lib/gamota-research-mcp/published-reports` and exposed read-only at `/reports/`. This keeps report data outside the frontend release directory so a UI deploy cannot delete published reports. The page never receives the MCP bearer token.

Build from the repository root:

```bash
cd web
npm ci
npm run build
```

Deploy the contents of `web/dist/` to `/var/www/gamota-research-ui/` (readable by Nginx). The live server keeps reports in `/var/lib/gamota-research-mcp/published-reports/`; Nginx serves that directory at `/reports/`. Update only the existing TLS server's `location /` to serve the UI directory and fall back to `index.html`:

```nginx
root /var/www/gamota-research-ui;
index index.html;

location / {
    try_files $uri $uri/ /index.html;
}

location /reports/ {
    alias /var/lib/gamota-research-mcp/published-reports/;
    add_header Cache-Control "no-cache, must-revalidate";
}
```

Keep the exact existing `location = /mcp` block, including upstream, auth, headers and streaming timeouts, unchanged. Keep the port 80 ACME challenge and HTTPS redirect unchanged. Validate and reload Nginx only:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

UI smoke checks:

```bash
curl -fsS -o /dev/null -w 'root=%{http_code}\n' https://52-64-163-35.sslip.io/
curl -sS -o /dev/null -w 'mcp=%{http_code}\n' https://52-64-163-35.sslip.io/mcp
```

Expected: `/` is `200`; unauthenticated `/mcp` remains `401`; `/reports/index.json` is `200`. Open the root and verify the published-report reader and evidence links. Then run `./deploy/verify.sh` with the bearer token in the protected operator environment to confirm authenticated initialization and 18-tool discovery. A frontend-only release must not restart `gamota-research-mcp.service`.

For rollback, restore the previous Nginx `location /` body and run `sudo nginx -t && sudo systemctl reload nginx`; the MCP block and systemd service need no change.
