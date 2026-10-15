# Mission 2 MVP Evaluator Runbook

> The official Mission 2 rubric was read from the authenticated portal on 2026-10-15. The hosted MCP endpoint is live and externally verified; see [`mission2-deployment-verification.md`](mission2-deployment-verification.md). H2 remains GAP only for the owner-dependent Mission 1 Q2 evidence and final submission audit. See `mission2-evidence-map.md` for criterion status and `mission2-evaluation-report.md` for the case inventory.

## 1. Prerequisites

- Linux or macOS shell
- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)
- Git checkout of this project
- Codex with MCP stdio support for the final host smoke

The host agent supplies its own planning and web search/fetch tools. Gamota Research MCP persists the host's research inputs, source/evidence/claim records, budgets and issues; returns traces and lineage audits; and performs deterministic validation/finalization. The MCP server does not perform general web search or call an LLM.

## 2. Locked environment setup

From the repository root:

```bash
uv sync --frozen
```

For an isolated verification environment, choose new empty paths and run:

```bash
FINAL_ENV=/tmp/gamota-research-mission2-final-env-20261015
FINAL_CACHE=/tmp/gamota-research-mission2-final-cache-20261015
FINAL_DIST=/tmp/gamota-research-mission2-final-dist-20261015

test ! -e "$FINAL_ENV"
test ! -e "$FINAL_CACHE"
test ! -e "$FINAL_DIST"
mkdir "$FINAL_DIST"

env -u VIRTUAL_ENV \
  UV_PROJECT_ENVIRONMENT="$FINAL_ENV" \
  UV_CACHE_DIR="$FINAL_CACHE" \
  uv sync --frozen --no-editable --python 3.13
```

If any chosen path already exists, stop and choose a new unique path. Do not remove or reuse research databases. `uv.lock` is the dependency source of truth.

## 3. Run the full test suite

```bash
env -u GAMOTA_RESEARCH_DB \
  -u GAMOTA_STORE_PROVIDER \
  PYTHONDONTWRITEBYTECODE=1 \
  "$FINAL_ENV/bin/python" \
  -m pytest -q -p no:cacheprovider
```

Record the command, exit code and collected/passed count. The suite covers research lifecycle and budgets, grounding, freshness, comparability/conflict, provenance/confidence, providers, store semantics, MCP protocol and stdio, plus scenario evaluations. A Python MCP protocol test is useful regression evidence but does not count as a real Codex-host smoke.

## 4. Build and verify the wheel

```bash
env UV_CACHE_DIR="$FINAL_CACHE" \
  uv build --wheel --out-dir "$FINAL_DIST"

WHEEL=$(find "$FINAL_DIST" -maxdepth 1 -name '*.whl' -print -quit)
test -n "$WHEEL"
sha256sum "$WHEEL"
unzip -l "$WHEEL" | grep 'gamota_research/fixtures/store_fixture.json'
```

For artifact-level verification, install the wheel into a separate clean environment and run the suite from a copied test tree outside the checkout, so the source tree cannot shadow the installed package. Record the wheel hash and test result. Do not copy build outputs into the repository.

## 5. Start the MCP server

The server uses stdio. Set a dedicated SQLite file before launching it:

```bash
GAMOTA_RESEARCH_DB=/tmp/gamota-research-evaluator.sqlite3 \
GAMOTA_STORE_PROVIDER=fixture \
"$FINAL_ENV/bin/python" -m gamota_research.mcp_server
```

For the AITC hosted deployment, follow [`deploy/README_DEPLOY.md`](../deploy/README_DEPLOY.md). It enables Streamable HTTP using `GAMOTA_TRANSPORT=streamable-http`; stdio remains the default. The deployment template binds to `127.0.0.1`, requires a static bearer token and the final public MCP resource URL, and expects TLS at the approved ingress. Do not attach a demo or evidence database to the hosted service.

Use a new, dedicated database path per disposable smoke. Keep Gate F and Gate G evidence databases immutable. The fixture provider is synthetic data; do not describe it as a market observation.

## 6. Verify the MCP surface and schemas

Connect with an MCP client and call `list_tools`. The expected surface has exactly these 18 tools:

1. `create_research_run`
2. `set_research_contract`
3. `update_research_progress`
4. `save_research_source`
5. `save_research_evidence`
6. `save_research_claim`
7. `record_research_issue`
8. `finalize_research_run`
9. `get_research_run`
10. `get_claim_trace`
11. `get_claim_lineage_audit`
12. `search_store_apps`
13. `get_game_details`
14. `get_store_chart_snapshot`
15. `get_store_chart_history`
16. `publish_game_decision_brief`
17. `list_published_reports`
18. `get_published_report`

Inspect schemas from the connected server rather than relying on a cached client view. Check that `save_research_claim` includes `existing_claim_id`; `finalize_research_run` includes `validate_only`; and `stop_reason` is optional when `validate_only=true` while normal finalization still requires a valid explicit reason.

## 7. Research lifecycle and interpretation

1. Create a run and persist its scope/contract before research.
2. The host agent performs web searches/fetches. Record host-reported searches/rounds through `update_research_progress`; MCP domain-tool counters are separate.
3. Save source metadata (the server records it; it does not fetch the URL), then atomic evidence with a quote, locator, metric/value and source mode.
4. Save claims linked to evidence. The validator checks grounding, metric compatibility, freshness, evidence slots, comparability, conflicts and provenance.
5. Use `get_claim_trace` to inspect claim → evidence → source. Use `get_claim_lineage_audit` to inspect direct documents and independent roots.
6. Call `finalize_research_run(validate_only=true)` to assess without persistence. Compare database hashes before and after if demonstrating purity.
7. If the assessment is complete and `finalize_allowed=true`, finalize with the appropriate explicit stop reason. If evidence is incomplete, still finalize with the matching stop reason so the PARTIAL/INSUFFICIENT_DATA result and its gaps are preserved; do not present it as complete. Read back the run, claim trace and lineage.
8. For reports, use `claim_type=ESTIMATE` for third-party estimates and `claim_type=RECOMMENDATION` for evidence-linked actions. After finalization, call `publish_game_decision_brief`; partial/insufficient-data runs can publish with unknowns visible. Read the result with `get_published_report`.

Budget semantics: a counter exactly at its limit means exhausted but remains within budget; only a counter greater than its limit is over budget. Validation-only is a pure assessment. For an existing claim, `save_research_claim(existing_claim_id=...)` preserves that claim and its evidence links; it may repair a null `target_metric` only under the tool's constrained rules and does not silently replace claim meaning.

## 8. Reproduce or inspect Gate F (recorded live research)

Gate F is a recorded host-native live research run, not a command that can be reproduced from the temporary DB alone. Its recorded DB is `/tmp/gamota-research-gate-f-20261015.sqlite3`; inspect it only through a read-only SQLite connection. To reproduce the workflow, use a new DB:

- Run `81229fe7-f9f5-4897-8c55-be6482326cd3`; status `COMPLETE`, stop reason `COVERAGE_SUFFICIENT`.
- Claim `738ca916-0f42-4502-9c40-76f27bf65b79` is `VALID / STRONG` for `open_beta_start_date`.
- Two supporting sources resolve to two independent roots; progress is 5/6 searches and 2/2 rounds, within budget.
- The host agent performed the web research; MCP stored and validated the submitted evidence.

Do not attach a write-capable server to the recorded Gate F database. For a new run, use a fresh DB, let the host do the live search, and preserve source URLs, quotes, timestamps, queries, progress and limitations.

## 9. Reproduce Gate G — Evidence Lineage Audit

Use a new dedicated DB and explicitly label all records synthetic/demo; do not use live web search. Create one demo run, three sources in a chain A → B → C (B's parent is A, C's parent is B; all resolve to A), one evidence item per source and exactly one claim linked to all three evidence items.

Expected invariant:

```text
supporting evidence = 3
direct source documents = 3
independent provenance roots = 1
```

Run `get_claim_trace` and `get_claim_lineage_audit`, then a validation-only assessment. The standout result is that three citations can still share one evidentiary origin; citation count does not establish independent corroboration. The recorded Gate G run is `b9c1b597-d8e1-497a-ba73-e48edaa51456`, with claim `e62aba02-97ce-4094-a0f3-b462ce74408a`, `VALID / MODERATE`, and informational `SHARED_ORIGIN`. Its recorded DB is `/tmp/gamota-research-gate-g-lineage-20261015.sqlite3`; it is separate from Gate F and must remain unchanged.

## 10. Codex setup

Use `config/codex-mcp.example.toml` as a template. Replace both project path placeholders with the absolute checkout path and configure a new dedicated smoke DB. The example file does not activate a server on its own. Confirm the effective command and environment with `codex mcp get gamota_research` before invoking a tool.

For the final acceptance smoke, configure Codex to launch the final verified environment/wheel installation, not a stale editable checkout. Use a separate Codex smoke DB. Never configure Gate F/G paths for write access.

## 11. Final Codex host smoke

Run only after official rubric reconciliation (H2) and any resulting changes. Ask Codex through the real connected MCP server to:

1. List all tools and report the count (expected: exactly 18).
2. Inspect the fresh schemas, including the finalization and existing-claim fields above.
3. Call `create_research_run` once with `Mission 2 final Codex MCP smoke test.`
4. Return the run ID; read the run back and verify it persisted in the dedicated Codex smoke DB.
5. Do not finalize the disposable smoke run.

Acceptance requires evidence from the actual Codex host: connection established, 18 tools listed, one successful MCP call and returned run ID, plus persistence readback. A direct Python MCP client alone does not satisfy this gate. The older fixture workflow in `tests/manual/codex_host_smoke.md` is an optional broader host integration check and must remain clearly labeled synthetic.

## 12. Troubleshooting

- **No tools / stale schemas:** verify `codex mcp get gamota_research`, command, working directory, Python environment and server restart; reconnect and inspect schemas again.
- **Database appears unexpected:** stop writes. Open it read-only, inspect tables/rows and before/after hashes, then use a new unique DB if contamination is possible. Never delete shards, research DBs or evidence artifacts as a recovery shortcut.
- **Validation fails:** inspect `get_research_run`, `get_claim_trace` and `get_claim_lineage_audit`; resolve evidence/contract gaps at the source. Do not weaken provenance rules to improve a demo result.
- **Fixture output appears:** report it as synthetic fixture output, never as a live market fact.
- **Codex blocks a call:** configure the approved action-time MCP access for the dedicated smoke DB, then reconnect. Record the host's actual tool-call evidence.

## 13. Final report checklist

Record the official rubric mapping status; Python/uv versions; full-suite command/result; wheel filename/hash/resource check; direct MCP tool count/schema/call/readback; real Codex tool count/schemas/call/run ID/readback; Gate F/G run IDs and immutable DB hashes; and final `git status --short --branch`. Keep build outputs, environments, caches and smoke databases outside the repository.
