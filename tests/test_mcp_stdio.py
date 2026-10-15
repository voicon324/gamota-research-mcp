from __future__ import annotations

import anyio
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_stdio_server_initializes_lists_tools_and_accepts_a_call(tmp_path):
    async def run():
        env = {**os.environ, "GAMOTA_RESEARCH_DB": str(tmp_path / "stdio.sqlite3")}
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "gamota_research.mcp_server"],
            env=env,
            cwd=PROJECT_ROOT,
        )
        with anyio.fail_after(20):
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tool_list = await session.list_tools()
                    discovered = {tool.name for tool in tool_list.tools}
                    existing = {
                        "create_research_run",
                        "set_research_contract",
                        "update_research_progress",
                        "save_research_source",
                        "save_research_evidence",
                        "save_research_claim",
                        "record_research_issue",
                        "finalize_research_run",
                        "get_research_run",
                        "get_claim_trace",
                        "get_claim_lineage_audit",
                    }
                    domain = {
                        "search_store_apps",
                        "get_game_details",
                        "get_store_chart_snapshot",
                        "get_store_chart_history",
                    }
                    assert len(discovered) == 18
                    assert {
                        "publish_game_decision_brief",
                        "list_published_reports",
                        "get_published_report",
                    } <= discovered
                    assert existing <= discovered
                    assert domain <= discovered
                    result = await session.call_tool(
                        "create_research_run",
                        {"question": "Subprocess stdio smoke test"},
                    )
                    assert result.is_error is False
                    run_id = result.structured_content["run_id"]
                    assert result.structured_content["status"] == "CREATED"
                    contract = await session.call_tool(
                        "set_research_contract",
                        {"run_id": run_id, "domain_tool_budget": 1},
                    )
                    assert contract.is_error is False
                    search = await session.call_tool(
                        "search_store_apps",
                        {
                            "run_id": run_id,
                            "store": "google_play",
                            "country": "VN",
                            "query": "orbit",
                        },
                    )
                    assert search.is_error is False
                    assert search.structured_content["source_mode"] == "FIXTURE"

    anyio.run(run)
