# AITC server deployment and operations

This bundle enables Streamable HTTP while preserving stdio. It also documents the current hosted deployment and retains the installation, verification and rollback procedure for future operations.

## Current deployment status (2026-10-15)

- Public MCP endpoint: `https://52.64.163.35/mcp` (bearer authentication required).
- The systemd application service and Nginx reverse proxy are active; the application binds to loopback behind Nginx.
- HTTPS is enabled with a Let's Encrypt IP certificate; automated renewal is configured.
- External MCP verification: unauthenticated request `401`; wrong bearer `401`; authenticated initialize `PASS`; authenticated discovery `15 tools`.
- The deployed checkout was read-only verified at revision `415e59513596fabd375cff2fbcc73817eb23375a`, clean, with both service and Nginx active.
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
- `GAMOTA_HOST` to `127.0.0.1` behind a reverse proxy (default)
- `PORT` to the locally reserved application port
- `GAMOTA_STORE_PROVIDER=fixture` for deterministic demo data, or explicitly choose `apple_rss` if live Apple Vietnam Top Free/Top Paid data is desired

Do not copy a development `.env`, SQLite DB, key, or bearer token into this bundle or Git. Do not pass the token as a command-line argument. Protect the environment file with owner-only read permissions.

### Authentication metadata limitation

The MCP SDK requires an `issuer_url` when configuring its bearer-verification middleware. This deployment uses the SDK's documented placeholder `https://auth.example.com`; it does **not** deploy an OAuth authorization server. Clients must be configured with the pre-shared bearer token directly. OAuth discovery/authorization clients are not supported by this static-token setup. The token value is never logged by the application.

## Install and operate

1. Review the repository revision and deployment files, then transfer the approved source/bundle using the server skill.
2. Install Python 3.13 and `uv` if not already present; create the service environment and run `uv sync --frozen --no-dev` from the install directory.
3. Create the persistent DB parent directory owned by the service user. Set up the environment file as described above.
4. Adapt `gamota-research-mcp.service` to the verified paths, user and port; install it with the operator's approved systemd procedure, reload systemd, enable and start it.
5. Configure the approved TLS ingress for `/mcp` to the local listener. Keep the bearer secret out of proxy access logs and diagnostic output.
6. Run `verify.sh` with the public URL and token supplied through a protected environment (never shell history). Confirm unauthenticated `401`, authenticated MCP initialization and tool discovery.
7. Capture only nonsecret evidence: service active, bound address/port, public URL, unauthenticated `401`, authenticated initialize pass, tool discovery pass. Never capture an Authorization header or token.

## Rollback

Stop and disable the service, restore the previous ingress route/configuration, and restore the prior application release. Keep the research database intact unless the owner separately approves a data migration/retention action. Rotate the bearer token if it may have been exposed. `rollback.sh` only stops/disables this service; the operator must verify the unit name before running it.

## Verification helper

`verify.sh` uses curl and Python's MCP client. Set `MCP_URL` and `GAMOTA_MCP_BEARER_TOKEN` in the protected shell environment, then execute the script. It prints status and tool count, never the token. A successful result is not evidence of public availability until run from the intended network path.
