# Manual Codex MCP host smoke

This is a manual check through the real Codex host. A Python MCP client test does not satisfy this gate.

## Scope and safety

- Use only the `fixture` provider and a fresh, dedicated SQLite database for each full smoke run. The example path is `/tmp/gamota-research-codex-smoke.sqlite3`; if it already contains data, choose a new path and point the Codex MCP configuration at it. Never delete an existing smoke database to make it fresh.
- Start a fresh Codex host/MCP server process for each full smoke run. `FixtureStoreProvider` advances through its dated chart snapshots on each chart call, so reusing a provider process can start the sequence at the wrong observation.
- This smoke makes no network requests. Its store observations are synthetic and must not be described as market findings.
- Do not enable the Apple RSS provider or add Claude configuration in this gate.
- Configure the MCP server only after the user confirms the action-time access change. Use the example entry in `config/codex-mcp.example.toml`, replacing both project-path placeholders with this checkout's absolute path. The example file itself does not activate the server.
- The MCP server can write research data to the configured SQLite database. Keep the smoke database separate from any existing research database.

## Host prompt

In Codex, ask it to run this checklist through the connected `gamota_research` MCP tools. Require it to show the tool names and returned IDs at each step, and stop if the server is unavailable or the fixture output differs from the assertions below.

> Run the Gamota Research MCP host smoke from `tests/manual/codex_host_smoke.md`. Use only synthetic fixture data and a fresh dedicated database path. Do not search the web or access Apple RSS. Show each MCP call and its returned IDs. Do not claim this demonstrates a real market finding. For write tools, use the host's approved tool-call workflow (this environment may require `--approve-for-me`).

## Assertions and sequence

1. Confirm Codex discovers exactly 15 tools, including `create_research_run`, `set_research_contract`, `search_store_apps`, `get_store_chart_snapshot`, `get_store_chart_history`, `save_research_source`, `save_research_evidence`, `save_research_claim`, `finalize_research_run`, `get_claim_trace`, `get_claim_lineage_audit`, and `get_research_run`.
2. Call `create_research_run` with question: `Verify synthetic fixture store-rank evidence through the real Codex host.` Save the returned `run_id`.
3. Call `set_research_contract` for that run with:
   - `decision_goal`: `Verify Codex can persist and validate synthetic store-rank evidence through Gamota MCP.`
   - `geography`: `["VN"]`
   - `time_scope`: `synthetic fixture snapshot`
   - `metrics`: `["store_rank"]`
   - `assumptions`: `["All store data in this smoke is synthetic fixture data, not a market observation."]`
   - `evidence_slots`: `["observed store_rank for the synthetic fixture game"]`
   - `planned_query_budget`: `1`
   - `domain_tool_budget`: `5`
   - `research_round_budget`: `1`
4. Call `search_store_apps` with `store="google_play"`, `country="VN"`, and `query="orbit"`. Confirm the result says `source_mode="FIXTURE"` and includes game ID `synthetic-orbit-quest`.
5. Call `get_store_chart_snapshot` with `store="google_play"`, `country="VN"`, `chart_type="top_free"`, and `limit=20`. This fixture schedule is stateful per provider instance. Confirm the first call has `source_mode="FIXTURE"`, `observed_at="2026-10-01T00:00:00+00:00"`, and `synthetic-orbit-quest` at rank `20`. Save this as snapshot 1; do not use it for the final claim.
6. Call `get_store_chart_snapshot` a second time with the same arguments. Confirm `source_mode="FIXTURE"`, `observed_at="2026-10-15T00:00:00+00:00"`, `synthetic-orbit-quest` at rank `8`, and a snapshot ID different from snapshot 1. Save this as snapshot 2, including its `source_url` and snapshot ID. Use snapshot 2 for the source, evidence, and rank claim below.
7. Call `get_store_chart_history` with the same `run_id`, `store="google_play"`, `country="VN"`, `chart_type="top_free"`, and `game_id="synthetic-orbit-quest"`. Confirm the observations are 2026-10-01 rank 20 and 2026-10-15 rank 8, with `rank_change=12` and `source_mode="FIXTURE"`.
8. Call `save_research_source` using the same `run_id`, snapshot 2's `source_url`, title `Synthetic fixture chart snapshot`, `source_type="STORE_LISTING"`, `provenance_status="ORIGINAL"`, and metadata marking `source_mode="FIXTURE"`, `generated_for_testing=true`, and snapshot 2's ID. Save the returned `source_id` and `root_source_id`.
9. Call `save_research_evidence` with the returned source ID, a quote derived from snapshot 2 (for example, `Synthetic fixture observation: synthetic-orbit-quest appears at rank 8.`), locator `snapshot <snapshot 2 ID>`, `metric="store_rank"`, `value=8`, `unit="rank_position"`, `market="VN"`, `source_mode="FIXTURE"`, and `metadata={"evidence_slots":["observed store_rank for the synthetic fixture game"]}`. Save the returned `evidence_id`.
10. Call `save_research_claim` with text exactly `This game's observed store rank is 8.`, `claim_type="FACT"`, `target_metric="store_rank"`, and the returned evidence ID. Save the returned `claim_id`.
11. Before finalizing, call `get_claim_trace` with the saved claim ID. Assert the trace links the claim to the saved evidence ID and source ID, and that the evidence metadata's `evidence_slots` contains exactly `observed store_rank for the synthetic fixture game`. Then call `get_research_run` and assert `evidence_slot_coverage.required` contains exactly that slot, `covered` contains it, `missing` is empty, and `complete=true`. These checks verify both the persisted evidence metadata and the repository's coverage calculation. If either assertion fails, stop and do not finalize.
12. Call `finalize_research_run` with `stop_reason="COVERAGE_SUFFICIENT"`. Confirm the claim is valid, the required slot remains covered, there is no blocking GAP for that slot, and inspect the run/claim status, confidence level, rationale, and issues. A fixture result is a host-integration proof, not evidence of live market performance.
13. Call `get_claim_trace` with the returned claim ID. Confirm it resolves to the saved evidence quote, locator, snapshot 2 source URL, and snapshot ID.
14. Call `get_claim_lineage_audit` with the claim ID. Confirm it returns one document/root for this synthetic source and resolves to snapshot 2 (2026-10-15, rank 8), not snapshot 1.
15. Disconnect/reconnect the MCP host using a new Codex host process while keeping the final smoke database unchanged. Call `get_research_run` with the run ID and confirm its finalized status, contract, claim, complete slot coverage, and issue state can still be read. Then call `get_claim_trace` and `get_claim_lineage_audit` again with the saved claim ID; confirm the evidence metadata still contains the exact required slot, and that trace/lineage still resolve to snapshot 2. Also confirm the configured database file exists. Do not request another chart snapshot during this persistence check because a new provider process resets the fixture schedule.

## Record the result

Capture the host name, config command/env/DB/provider (no secrets), approval mode used for write tools, discovered tool count, both snapshot IDs and dates/ranks, history movement, `run_id`, `source_id`, `evidence_id`, `claim_id`, finalize output, trace, lineage audit, reconnect result, and any errors. Mark each check PASS/FAIL. The gate passes only through actual Codex calls; do not substitute protocol tests for host evidence.
