# Mission 3 A1 deployment verification

Date: 2026-10-23 (ICT)

## Release

- Repository: `voicon324/gamota-research-mcp`
- Deployed commit: `01b2e1aa808e7b8550c0d7923d6027c3399d4cda`
- Demo: <https://52.64.163.35/>
- MCP: <https://52.64.163.35/mcp>
- Backend module updated: `/opt/gamota-research-mcp/src/gamota_research/reports.py`
- Previous module preserved at `/opt/gamota-research-mcp/src/gamota_research/reports.py.before-mission3-01b2e1a`
- Static frontend files updated under `/var/www/gamota-research-ui/`; published report data was not changed.
- `gamota-research-mcp.service` was restarted and is active. Nginx remained active; its configuration was not changed or reloaded.

## Public smoke

| Check | Result |
|---|---|
| Website `/` | HTTP 200 |
| Unauthenticated `/mcp` | HTTP 401 (auth still enforced) |
| Published report index `/reports/index.json` | HTTP 200 |
| New CSS asset | HTTP 200 |
| New JavaScript asset | HTTP 200 |
| Root page references the new JavaScript asset | PASS |
| MCP service and Nginx | Active |

The browser loaded the new site and its report list. The library still contains the existing Pokémon TCG Pocket brief; no synthetic A1 report was inserted into production. The A1 examples in the automated tests and video are explicitly synthetic fixtures, not market research findings. The A1 conflict panel is shown when a connected agent publishes a report containing a comparable conflict.

## Local verification

- `uv run pytest tests/test_mission3_a1.py -q` — 9 passed.
- `uv run pytest -q` — 110 passed.
- `cd web && npm run build` — passed.
- Remotion composition/lint — passed; MP4 rendered at 1280×720, 30 fps, 95 seconds.
- `git diff --check` — passed.

No bearer token, environment contents, private key or authentication header is recorded here.
