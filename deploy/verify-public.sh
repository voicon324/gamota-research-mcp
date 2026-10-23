#!/usr/bin/env bash
set -euo pipefail

: "${MCP_URL:?Set MCP_URL to the public unauthenticated HTTPS MCP endpoint}"

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd -- "$script_dir/.." && pwd)
cd "$project_root"

uv run python - <<'PY'
import asyncio
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client(os.environ["MCP_URL"]) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            required = {"create_research_run", "publish_game_decision_brief"}
            missing = required - names
            if missing:
                raise SystemExit(f"Required public tools missing: {sorted(missing)}")
            print(f"Unauthenticated MCP initialize: PASS; tools: {len(names)}; write/publish: PASS")

asyncio.run(main())
PY
