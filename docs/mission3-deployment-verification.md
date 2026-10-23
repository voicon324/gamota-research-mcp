# Mission 3 A1 deployment verification

Date: 2026-10-23 (ICT)

## Release

- Repository: `voicon324/gamota-research-mcp`
- Backend/report release commit: `01b2e1aa808e7b8550c0d7923d6027c3399d4cda`
- Frontend Mission 3 label commit: `1de3dec338bca7ccf1ca1eb74788b4f6c786c467`
- Demo: <https://52.64.163.35/>
- MCP: <https://52.64.163.35/mcp>
- Backend module updated: `/opt/gamota-research-mcp/src/gamota_research/reports.py`
- Previous module preserved at `/opt/gamota-research-mcp/src/gamota_research/reports.py.before-mission3-01b2e1a`
- Static frontend files updated under `/var/www/gamota-research-ui/`.
- The live `index.html` before the final label refresh was preserved at `/var/www/gamota-research-ui/index.html.before-mission3-1de3dec`.
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
| Browser displays `RESEARCH OPERATIONS · MISSION 03 / A1` | PASS |
| MCP service and Nginx | Active |

The browser loaded the updated site and confirmed the A1 review panel renders source excerpts and comparison reasons. A live sourced report was later published through the authenticated MCP lifecycle; see the evidence below. The conflict test fixtures and video example remain synthetic and are labeled as such.

## Authenticated MCP and live research run

- No bearer: initialize returned HTTP 401; wrong bearer: HTTP 401.
- Server-side credential: authenticated initialize passed; `list_tools` returned 18 tools. Credential and authorization headers are not recorded.
- Run `7b5bf83a-5be3-4f7b-9b55-0a6a6e9e21ad`: COMPLETE, MODERATE confidence; 3/3 claims VALID; 2/2 evidence slots covered; zero store-domain calls.
- The live research recorded Sensor Tower's 2023 global mobile-game consumer spend estimate (−2% YoY) and Unity's 2023 worldwide DAU growth (+4.1% in its measured game-app cohort). The sources measure different metrics and sample populations.
- Validator outcome: **NOT_COMPARABLE**, reasons `metric_mismatch` and `sample_scope_mismatch`; it did not characterize this as a true conflict.
- Published brief: [`2023 Mobile Games: Spending and Activity Signals`](https://52.64.163.35/reports/global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682/report.json) (2 sources, 2 evidence records, 1 recommendation, 1 open NOT_COMPARABLE issue).
- Browser verified the report in the live library, including both quoted excerpts, publication dates, provenance labels, clickable source URLs and the NOT_COMPARABLE explanation.
- No application code or service restart was needed for this report; it used the already deployed release and updated the production report library through MCP.

## Local verification

- `uv run pytest tests/test_mission3_a1.py -q` — 9 passed.
- `uv run pytest -q` — 110 passed at the deployment checkout. A fresh run against the current working tree on 2026-10-23 passed all 131 tests.
- `cd web && npm run build` — passed.
- Remotion composition/lint — passed; MP4 rendered at 1280×720, 30 fps, 95 seconds.
- `git diff --check` — passed.

No bearer token, environment contents, private key or authentication header is recorded here.
