# Mission 2 hosted deployment verification

Verification date: 2026-10-15
Endpoint: <https://52.64.163.35/mcp>
Transport: MCP Streamable HTTP over HTTPS with static bearer authentication

## External MCP smoke

The verifier was run from the development machine against the public endpoint, outside the EC2 instance:

| Check | Result |
|---|---|
| Request without bearer token | HTTP 401, expected |
| Request with wrong bearer token | HTTP 401, expected |
| Authenticated MCP initialize | PASS |
| Authenticated tool discovery | PASS — 15 tools |

The bearer value and Authorization headers are intentionally omitted from this record, screenshots, video and repository.

## Server provenance and service state

A read-only SSH check on 2026-10-15 reported:

- Deployed checkout revision: `415e59513596fabd375cff2fbcc73817eb23375a`
- Deployed checkout status: clean
- `gamota-research-mcp.service`: active
- `nginx`: active
- Nginx terminates public HTTPS and proxies `/mcp` to the loopback MCP service.
- The IP TLS certificate was issued by Let's Encrypt and automatic renewal is configured.

The service environment, bearer token, private key, private addresses, database contents and Authorization headers are not included. The endpoint is bearer-protected; provide evaluator credentials only through an organizer-approved private channel if one is available. Otherwise, use this sanitized verification record and the local run instructions.

## Reproduction pointers

- `deploy/README_DEPLOY.md` documents deployment and operations.
- `deploy/verify.sh` describes the authenticated protocol checks without printing the token.
- `docs/mission2-runbook.md` documents the local stdio path.
