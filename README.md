# Gamota Research MCP

**Turn game-market research into a report you can check.** Codex or Claude does the web search with its own tools. Gamota Research MCP records sources and evidence, checks claims and uncertainty, then publishes a Game Decision Brief for review.

## The workflow

1. Ask a focused question: game, market, platform, metric and time period.
2. The agent searches and reads public sources using its native web tools.
3. It records source details, quoted evidence and claims in the MCP.
4. The MCP checks evidence links, scope, dates, metrics, conflicts and source independence. If evidence is missing, the result can remain partial; the agent should not guess.
5. The agent publishes the brief. Open it in the report library and inspect the evidence behind each finding.

The MCP does **not** perform general web search or call an LLM. It is the research record, validator and report publisher.

## What the report contains

A Game Decision Brief includes the research question and scope, executive verdict and confidence, market signals, findings with evidence and source links, evidence-backed recommendations, unknowns and issues, methodology, and JSON/Markdown downloads. Estimates and inferences are labeled separately from facts.

## Try it with Codex

Requires Python 3.13 and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --frozen
```

Add the server entry from [`config/codex-mcp.example.toml`](config/codex-mcp.example.toml) to your Codex MCP configuration. Replace `/ABSOLUTE/PATH/TO/gamota-research-mcp` with this checkout's path. To see locally published reports on the local website, set `GAMOTA_REPORTS_DIR` in that entry to `<checkout>/web/public/reports`. The example uses a disposable database and synthetic store data; the agent still does web research with its own tools. Restart Codex and check the connection:

```bash
codex mcp list
```

Then ask Codex to research a question like:

> Research whether **[game]** shows **[market signal]** in **[market]** on **[platform]** during **[period]**. Use your native web search and fetch tools. Create a research run and contract; save each source and quoted evidence before claims; label facts, estimates and inferences; record gaps or conflicts; validate and finalize; then publish a Game Decision Brief. Do not fill missing evidence with guesses.

For the live [report library](https://52-64-163-35.sslip.io/#published), connect to the hosted MCP at `https://52-64-163-35.sslip.io/mcp-public`. No login or bearer token is required.

## Connect ChatGPT, Codex, or Claude

In ChatGPT, use the **Gamota Research Public** connector. To add it to another ChatGPT profile, add a custom MCP server with this endpoint and choose no authentication:

```text
https://52-64-163-35.sslip.io/mcp-public
```

For Codex or Claude, add the same endpoint to the client's MCP settings with authentication disabled:

```toml
[mcp_servers.gamota-research]
url = "https://52-64-163-35.sslip.io/mcp-public"
```

Your agent uses its own web search and fetch tools; Gamota Research stores sources and evidence, checks the report, and publishes it to the shared library.

**Public access:** this endpoint exposes every MCP tool, including creating and updating research and publishing reports. Anyone with the URL can use those tools. Use public information only; do not send private or confidential data.

## Run locally

The Codex configuration above starts the local MCP automatically. To run it manually for another MCP client, use stdio mode with a disposable database and synthetic store data:

```bash
GAMOTA_RESEARCH_DB=/tmp/gamota-research-demo.sqlite3 \
GAMOTA_STORE_PROVIDER=fixture \
uv run python -m gamota_research.mcp_server
```

To run the website in a second terminal:

```bash
cd web
npm ci
npm run dev
```

The local website is available at `http://localhost:5173` and reads reports from `web/public/reports`. Set `GAMOTA_REPORTS_DIR` to that folder in the MCP client's configuration to see local reports there.

## Development checks

```bash
uv run pytest -q
cd web && npm run build
```

## More detail

- [Mission 3 A1 — conflicting sources: change, evidence and answers](docs/mission3-a1.md)
- [Codex smoke and research lifecycle runbook](docs/mission2-runbook.md)
- [Deployment and operations](deploy/README_DEPLOY.md)
- [Mission 2 evidence map](docs/mission2-evidence-map.md)
- [AI evidence log](docs/ai-evidence-log.md)
