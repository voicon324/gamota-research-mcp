# Gamota Research MCP

An evidence-first research MVP for mobile-game market questions. The central hypothesis is that an AI research agent can produce more decision-ready findings when it records atomic evidence, checks source lineage and uncertainty, and lets a reviewer trace each claim back to its source.

The host agent (such as Codex or Claude) performs web search and fetch with its native tools. This MCP server persists research state and applies deterministic grounding, freshness, metric-compatibility, comparability, conflict and provenance checks. It does not perform general web search or call an LLM.

## What the MCP server does

The MCP server exposes 18 tools. It persists research runs, contracts, progress, sources, evidence, claims and issues in SQLite; returns claim-to-source traces; audits source-root lineage; validates/finalizes research deterministically; and publishes validated Game Decision Briefs as JSON/Markdown artifacts with a report-library manifest. It also exposes bounded game/store tools through an explicit provider.

The host agent (such as Codex or Claude) plans the research and performs web search/fetch with its own available tools. The MCP server does not perform general web search or call an LLM: it records host-provided URLs, quotations, evidence and claims, then checks grounding, freshness, metric compatibility, comparability, conflicts and provenance. Host-reported search counts are recorded separately from MCP domain-tool calls because the server cannot enforce or observe searches performed by the host.

## Agent research → published report

Use Codex or Claude as the research agent. A typical request is: “Research whether [game] shows [specific market/product signal] in [market/platform/time period]. Use your native web search and fetch tools. Create a Gamota research run and contract, save each source and verbatim evidence before claims, distinguish facts from estimates and inferences, record gaps/conflicts, validate and finalize, then publish a Game Decision Brief. Do not fill missing evidence with guesses.”

The agent calls `publish_game_decision_brief` only after finalization and provides the report title, game, and its concise executive verdict. The compiler takes findings and evidence from validated MCP claims; only `RECOMMENDATION` claims with linked evidence become report actions. `ESTIMATE` claims remain visibly labeled estimates. `list_published_reports` and `get_published_report` let agents inspect published output. Publishing writes immutable `report.json`, `report.md`, and `index.json` files under `GAMOTA_REPORTS_DIR`. On the hosted site, this directory is served read-only under `/reports/`; the browser never receives the MCP bearer token.

The fixture store provider is synthetic test data. The Apple RSS provider is a separate explicit live store-data option; it is not used by the fixture smoke. Neither provider changes the host agent's responsibility for web research. Values in automated tests and fixture demonstrations are not market findings.

## Online research desk

The public UI at [https://52.64.163.35/](https://52.64.163.35/) centers the published-report library, which reads the canonical manifest and reports from `/reports/`; selecting a finding opens its evidence and source. Historical R1/R2 research examples sit in a collapsed reference section and are labeled as examples rather than MCP-published reports. Publishing through MCP does not start a web search itself. The page can check that `/mcp` responds with the expected unauthenticated `401` and includes a copyable Codex connection template. The bearer token is never stored in or sent by the UI.

The agent (Codex or Claude) uses its own search tools and connects to the hosted Streamable HTTP MCP endpoint at [https://52.64.163.35/mcp](https://52.64.163.35/mcp). The static UI and MCP route share the HTTPS origin but remain separate: Nginx serves `/` and proxies `/mcp` to the authenticated Python service. See [deployment operations](deploy/README_DEPLOY.md#static-research-ui) for publishing UI updates without restarting MCP.

The official Mission 2 rubric was read from the authenticated portal on 2026-10-15. Implementation and submission evidence are tracked separately; current status and remaining proof are in the [evidence map](docs/mission2-evidence-map.md). The [evaluation report](docs/mission2-evaluation-report.md) records eight executable behavioral cases and two completed real-web research trials. AI usage and decisions are recorded in the [AI evidence log](docs/ai-evidence-log.md).

## Run locally

Requires Python 3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --frozen
uv run pytest -q
```

To start the stdio MCP server with the synthetic fixture provider and keep its disposable database outside the repository:

```bash
GAMOTA_RESEARCH_DB=/tmp/gamota-research-demo.sqlite3 \
GAMOTA_STORE_PROVIDER=fixture \
uv run python -m gamota_research.mcp_server
```

Configure Codex using [`config/codex-mcp.example.toml`](config/codex-mcp.example.toml); replace its checkout-path and database placeholders, then follow the connection checks in the [runbook](docs/mission2-runbook.md#10-codex-setup). The `fixture` provider contains synthetic test data, not market observations. The Apple RSS provider is a separate explicit live store-data option.

For hosted use, set `GAMOTA_TRANSPORT=streamable-http` with a bearer token and public resource URL; stdio remains the default. See the [AITC deployment and operations guide](deploy/README_DEPLOY.md) for the service template, configuration variables and verification steps. The HTTP endpoint is `/mcp` and binds to localhost unless explicitly configured otherwise.

Set `GAMOTA_REPORTS_DIR` to a persistent report directory. For the public hosted reader it must match the Nginx `/reports/` alias described in the deployment guide. The local default is `web/public/reports` under the server working directory, so Vite serves published artifacts during local development.

## Mission 2 evidence and submission status

- **Core slice selected:** host-orchestrated research with MCP-backed evidence persistence, claim traceability and deterministic validation. Canonical R1/R2 real-web artifacts and a separate synthetic lineage demonstration are described in the evidence map.
- **Evaluation:** eight automated behavioral cases and two real end-to-end cases are recorded in Expected → Actual → Pass/Fail → Learning format. After the report-pipeline release, the current tree passed 101 tests and 8 evals; the frontend production build also passed.
- **Q1 draft:** the selected slice is the evidence-backed research loop because it tests whether an agent's findings can be checked, challenged and limited by source quality instead of relying on fluent text alone. The evidence map contains the implementation/runtime pointers. This draft still needs owner review.
- **Q2 (Mission 1 decision change):** pending owner-provided Mission 1 decision and the evidence that led to any change. No change is inferred here.
- **Q3 (current limitation and next priority):** R2 exposes strict scope/date/metric grounding when the exact required evidence is unavailable. The next technical priority is better date/amount normalization and source handling without weakening safe-stop behavior. The hosted HTTP deployment is complete; the report distinguishes actual hard-case evidence from synthetic tests.
- **AI Evidence Log:** see [`docs/ai-evidence-log.md`](docs/ai-evidence-log.md); entries distinguish recorded facts from items that still need owner confirmation.
- **Online demo:** Hosted Streamable HTTP MCP is live at [https://52.64.163.35/mcp](https://52.64.163.35/mcp) and requires a bearer token. It exposes 18 tools, including report publishing/list/read. The website and published report library are at [https://52.64.163.35/](https://52.64.163.35/). See the sanitized [deployment verification record](docs/mission2-deployment-verification.md). Never publish the bearer value; provide it only through an organizer-approved private channel if one is available. Local stdio instructions remain above.
- **Presentation video:** A short presentation is prepared as a separate submission artifact and provided locally for upload. The video file and its Remotion source are intentionally excluded from the public repository.
- **Public repository:** [voicon324/gamota-research-mcp](https://github.com/voicon324/gamota-research-mcp) contains the source, tests and review artifacts. It does not contain the video or video-generation source.

SQLite uses Python's standard library. Tests use temporary databases; commands above keep manual demo state in `/tmp` rather than the workspace root.
