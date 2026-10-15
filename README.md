# Gamota Research MCP

An evidence-first research MVP for mobile-game market questions. The central hypothesis is that an AI research agent can produce more decision-ready findings when it records atomic evidence, checks source lineage and uncertainty, and lets a reviewer trace each claim back to its source.

The host agent (such as Codex or Claude) performs web search and fetch with its native tools. This MCP server persists research state and applies deterministic grounding, freshness, metric-compatibility, comparability, conflict and provenance checks. It does not perform general web search or call an LLM.

## What the MCP server does

The MCP server exposes 15 tools. It persists research runs, contracts, progress, sources, evidence, claims and issues in SQLite; returns claim-to-source traces; audits source-root lineage; and validates or finalizes research deterministically. It also exposes bounded game/store tools through an explicit provider.

The host agent (such as Codex or Claude) plans the research and performs web search/fetch with its own available tools. The MCP server does not perform general web search or call an LLM: it records host-provided URLs, quotations, evidence and claims, then checks grounding, freshness, metric compatibility, comparability, conflicts and provenance. Host-reported search counts are recorded separately from MCP domain-tool calls because the server cannot enforce or observe searches performed by the host.

The fixture store provider is synthetic test data. The Apple RSS provider is a separate explicit live store-data option; it is not used by the fixture smoke. Neither provider changes the host agent's responsibility for web research. Values in automated tests and fixture demonstrations are not market findings.

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

## Mission 2 evidence and submission status

- **Core slice selected:** host-orchestrated research with MCP-backed evidence persistence, claim traceability and deterministic validation. Canonical R1/R2 real-web artifacts and a separate synthetic lineage demonstration are described in the evidence map.
- **Evaluation:** eight automated behavioral cases and two real end-to-end cases are recorded in Expected → Actual → Pass/Fail → Learning format. The post-HTTP working tree has 97 passing tests and 8 passing evals; rerun after any further code change.
- **Q1 draft:** the selected slice is the evidence-backed research loop because it tests whether an agent's findings can be checked, challenged and limited by source quality instead of relying on fluent text alone. The evidence map contains the implementation/runtime pointers. This draft still needs owner review.
- **Q2 (Mission 1 decision change):** pending owner-provided Mission 1 decision and the evidence that led to any change. No change is inferred here.
- **Q3 (current limitation and next priority):** R2 exposes strict scope/date/metric grounding when the exact required evidence is unavailable. The next technical priority is better date/amount normalization and source handling without weakening safe-stop behavior. The hosted HTTP deployment is complete; the report distinguishes actual hard-case evidence from synthetic tests.
- **AI Evidence Log:** see [`docs/ai-evidence-log.md`](docs/ai-evidence-log.md); entries distinguish recorded facts from items that still need owner confirmation.
- **Online demo:** Hosted Streamable HTTP MCP is live at [https://52.64.163.35/mcp](https://52.64.163.35/mcp) and requires a bearer token. External verification returned 401 without a token and with a wrong token; authenticated initialize and discovery of all 15 tools passed. See the sanitized [deployment verification record](docs/mission2-deployment-verification.md). Never publish the bearer value; provide it only through an organizer-approved private channel if one is available. Local stdio instructions remain above.
- **Presentation video:** A short presentation is prepared as a separate submission artifact and provided locally for upload. The video file and its Remotion source are intentionally excluded from the public repository.
- **Public repository:** [voicon324/gamota-research-mcp](https://github.com/voicon324/gamota-research-mcp) contains the source, tests and review artifacts. It does not contain the video or video-generation source.

SQLite uses Python's standard library. Tests use temporary databases; commands above keep manual demo state in `/tmp` rather than the workspace root.
