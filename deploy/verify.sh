#!/usr/bin/env bash
set -euo pipefail

: "${MCP_URL:?Set MCP_URL to the HTTPS MCP endpoint ending in /mcp}"
: "${GAMOTA_MCP_BEARER_TOKEN:?Set the bearer token through a protected environment}"

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd -- "$script_dir/.." && pwd)
cd "$project_root"

unauth_status=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"deployment-smoke","version":"1.0"}}}')
printf 'Unauthenticated MCP initialize: HTTP %s (expected 401)\n' "$unauth_status"
test "$unauth_status" = 401

wrong_token_status=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$MCP_URL" \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -H 'Authorization: Bearer invalid-deployment-smoke-token' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"deployment-smoke","version":"1.0"}}}')
printf 'Wrong bearer MCP initialize: HTTP %s (expected 401)\n' "$wrong_token_status"
test "$wrong_token_status" = 401

uv run python - <<'PY'
import asyncio
import os
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

async def main():
    url = os.environ["MCP_URL"]
    token = os.environ["GAMOTA_MCP_BEARER_TOKEN"]
    async with create_mcp_http_client(headers={"Authorization": f"Bearer {token}"}) as http:
        async with streamable_http_client(url, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                print(f"Authenticated MCP initialize: PASS; tool discovery: PASS ({len(tools.tools)} tools)")

asyncio.run(main())
PY
