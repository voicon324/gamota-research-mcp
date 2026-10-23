# Mission 3 A1 deployment verification

Date: 2026-10-23 (ICT)

## Release

- Repository: `voicon324/gamota-research-mcp`
- Backend/report release commit: `01b2e1aa808e7b8550c0d7923d6027c3399d4cda`
- Frontend Mission 3 label commit: `1de3dec338bca7ccf1ca1eb74788b4f6c786c467`
- Demo: <https://52-64-163-35.sslip.io/>
- MCP: <https://52-64-163-35.sslip.io/mcp>
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
- Published brief: [`2023 Mobile Games: Spending and Activity Signals`](https://52-64-163-35.sslip.io/reports/global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682/report.json) (2 sources, 2 evidence records, 1 recommendation, 1 open NOT_COMPARABLE issue).
- Browser verified the report in the live library, including both quoted excerpts, publication dates, provenance labels, clickable source URLs and the NOT_COMPARABLE explanation.
- No application code or service restart was needed for this report; it used the already deployed release and updated the production report library through MCP.

## Local verification

- `uv run pytest tests/test_mission3_a1.py -q` — 9 passed.
- `uv run pytest -q` — 110 passed at the deployment checkout. A fresh run against the current working tree on 2026-10-23 passed all 131 tests.
- `cd web && npm run build` — passed.
- Remotion composition/lint — passed; MP4 rendered at 1280×720, 30 fps, 95 seconds.
- `git diff --check` — passed.

No bearer token, environment contents, private key or authentication header is recorded here.

## Canonical HTTPS verification (2026-10-24)

The canonical hostname is `52-64-163-35.sslip.io`; the numeric IP does not match the server TLS certificate and fails hostname validation in current clients. Use the hostname for reviewer links.

| Check | Result |
|---|---|
| `https://52-64-163-35.sslip.io/` | HTTP 200 |
| `/reports/index.json` | HTTP 200; 5 published reports |
| Honor of Kings report JSON | HTTP 200; schema 1.0, published |
| `POST /mcp-public` initialize | HTTP 200 |
| `tools/list` after initialize | HTTP 200; 18 tools |
| Current deployed JS asset | HTTP 200; includes `ABSTAIN`, `NOT_COMPARABLE`, and `directional_decision` review UI |

The current live Sensor Tower/Unity example classifies its opposing-looking observations as `NOT_COMPARABLE` because metric and sample scope differ. It is a real scope-mismatch example, not a same-scope conflict. The comparable opposite-evidence `ABSTAIN` path is covered by the deterministic synthetic fixture and is labeled as such in the demo.

## Final submission verification (2026-10-24)

These checks were rerun while the code checkout was at `8b95cad292979d706c57935eaa2593f7809c5c55`, which matched `origin/main`. The only repository change after that verification is this documentation update.

| Check | Result |
|---|---|
| `uv run pytest -q` | 131 passed in 38.33s |
| `cd web && npm run build` | PASS (`tsc -b` and Vite production build) |
| Live app `/` | HTTP 200 |
| Published Honor of Kings report JSON | HTTP 200 |
| Demo MP4 | H.264/AAC, 1280×720, 165.653s (2:45.653) |

The final MP4 and Vietnamese SRT are delivered outside this repository. The portal's video URL remains blank for the user's YouTube upload.
