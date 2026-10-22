#!/usr/bin/env bash
set -Eeuo pipefail

: "${MCP_URL:?Set MCP_URL to the public HTTPS MCP endpoint ending in /mcp}"

issuer_url=${OAUTH_ISSUER_URL:-${MCP_URL%/mcp}}
issuer_url="${issuer_url%/}/"
resource_metadata_url="${MCP_URL%/mcp}/.well-known/oauth-protected-resource/mcp"
authorization_metadata_url="${issuer_url}/.well-known/oauth-authorization-server"
resource_file=$(mktemp)
authorization_file=$(mktemp)
unauth_file=$(mktemp)
headers_file=$(mktemp)
trap 'rm -f -- "$resource_file" "$authorization_file" "$unauth_file" "$headers_file"' EXIT

resource_status=$(curl -sS -o "$resource_file" -w '%{http_code}' "$resource_metadata_url")
test "$resource_status" = 200
python3 - "$resource_file" "$MCP_URL" "$issuer_url" <<'PY'
import json, sys
metadata = json.load(open(sys.argv[1], encoding="utf-8"))
assert metadata["resource"] == sys.argv[2], metadata
assert sys.argv[3] in metadata["authorization_servers"], metadata
print("Protected Resource Metadata: PASS (JSON, expected resource and issuer)")
PY

authorization_status=$(curl -sS -o "$authorization_file" -w '%{http_code}' "$authorization_metadata_url")
test "$authorization_status" = 200
python3 - "$authorization_file" "$issuer_url" <<'PY'
import json, sys
metadata = json.load(open(sys.argv[1], encoding="utf-8"))
assert metadata["issuer"] == sys.argv[2], metadata
assert "S256" in metadata["code_challenge_methods_supported"], metadata
assert metadata["token_endpoint_auth_methods_supported"] == ["none"], metadata
assert {"research:read", "research:write", "report:publish"}.issubset(metadata["scopes_supported"]), metadata
assert "registration_endpoint" not in metadata, metadata
print("Authorization Server Metadata: PASS (JSON, PKCE S256, fixed public client)")
PY

unauth_status=$(curl -sS -D "$headers_file" -o "$unauth_file" -w '%{http_code}' \
  -X POST "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"oauth-discovery-smoke","version":"1.0"}}}')
test "$unauth_status" = 401
grep -qi 'WWW-Authenticate:.*resource_metadata=' "$headers_file"
printf 'Unauthenticated MCP challenge: PASS (HTTP %s with resource metadata URL)\n' "$unauth_status"
