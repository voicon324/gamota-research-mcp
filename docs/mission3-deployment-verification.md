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

## Historical submission verification checkpoint (2026-10-24)

These checks were rerun while the code checkout was at `8b95cad292979d706c57935eaa2593f7809c5c55`, which matched `origin/main`. They describe the earlier checkpoint, before the subsequent Mission 3 A1.1/common-requirement follow-ups.

| Check | Result |
|---|---|
| `uv run pytest -q` | 131 passed in 38.33s |
| `cd web && npm run build` | PASS (`tsc -b` and Vite production build) |
| Live app `/` | HTTP 200 |
| Published Honor of Kings report JSON | HTTP 200 |
| Demo MP4 | H.264/AAC, 1280×720, 165.653s (2:45.653) |

The MP4 and Vietnamese SRT are delivered outside this repository. The portal's video URL remains blank for the user's YouTube upload.

## Common-requirement follow-up deployment (2026-10-24)

- GitHub branch: `mission3-a11-source-verification`, commit `9a7a568` (`Improve Mission 3 evidence freshness and report gaps`). It preserves the Mission 2 history and includes the Mission 3 A1/A1.1 work.
- Local verification on that commit: `uv run pytest -q` — **138 passed**; `cd web && npm run build` — passed.
- The code and static assets were deployed to the existing EC2 instance without changing Nginx configuration or the published-report database. Existing server-side work was preserved; backups of `validator.py`, `reports.py`, and the UI `index.html` were created alongside the originals.
- `gamota-research-mcp.service` restarted and is active.
- Post-deploy SHA-256 values for both backend modules, `index.html`, and the new CSS/JS assets matched the local build.
- Public checks: homepage `/` HTTP 200; `/reports/index.json` HTTP 200 and five reports listed; new JS asset HTTP 200; unauthenticated `/mcp` HTTP 401.
- Chrome loaded the deployed Fieldnotes site and showed the updated UI and five existing reports.
- This release does not change the report schema or MCP API. The YouTube video URL remains for the user's upload.
- The updated local Mission 3 video candidate is `gamota-mission3-demo-final-v3.mp4` (200.512 seconds, under the five-minute limit); its Vietnamese subtitle file is `gamota-mission3-demo-final-v3.vi.srt`. It corrects the prior 135-test narration/display to 138 and adds a clearly labeled common-requirement evidence chapter while retaining the real ChatGPT Web research footage. Both artifacts are delivered outside the repository for YouTube upload.

## Evidence-review workflow release (2026-10-24)

- GitHub branch: `mission3-a11-source-verification`, release head `23e9d3e` (`Remove obsolete frontend bundle`), including `709e47c` (`Preserve evidence context in research follow-ups`) and the evidence-review workflow commit `8303947`.
- Local verification: `uv run pytest tests/test_mission3_a1.py -q` — **19 passed**; `uv run pytest -q` — **146 passed**; `cd web && npm run build` — passed; `git diff --check` — clean.
- The server checkout had unrelated uncommitted changes, so it was left untouched. The exact release `reports.py` was installed into the active OAuth checkout after preserving `/opt/gamota-research-mcp-oauth/src/gamota_research/reports.py.before-709e47c`. The old UI index was preserved at `/var/www/gamota-research-ui/index.html.before-23e9d3e`; content-addressed old assets were retained.
- Backend module and static bundle SHA-256 values matched the local release: `reports.py` `b980e5a606061aafbb7c93eb2af21a67338e57daa8f5f213e79243e365cf323d`; UI `index.html` `7f3d03896818368150d0ab08d9e82ddcf6767dce94b6ea8031d02b04ad4ac35d`; JS `index-C8UlaRuN.js` `87a81ddd8773c6044904d71717567c0013d7c380c24a6dfc428c8ba298b14b89`; CSS `index-Di2oCKDQ.css` `4c786fee082a6e08ad6a4d55748dbeec056bcdec9702e253fe1c01220223bf8d`.
- `reports.py` compiled with the service virtualenv's Python. `gamota-research-mcp.service` restarted and reports `active`.
- Live smoke results: `/` HTTP 200; `/reports/index.json` HTTP 200; new JS and CSS assets HTTP 200; unauthenticated `/mcp` HTTP 401; `/mcp-public` initialize HTTP 200 and `tools/list` HTTP 200 with 18 tools.
- Nginx configuration and the published-report database were not changed. The release adds report-reader and follow-up context fields without changing the report schema or MCP tool manifest. The YouTube video upload remains for the user.

### Unavailable-evidence edge-case patch

- Added a regression for stale issue references whose evidence record is absent from the published report. The report now lists that ID under `unavailable_evidence_ids` only, so it cannot be mistaken for a valid linked citation or fail report validation.
- Local checks: focused test passed; `uv run pytest tests/test_mission3_a1.py -q` — **20 passed**; `uv run pytest -q` — **147 passed**; `git diff --check` — clean. Frontend was unchanged from the already verified production build.
- Backend-only patch `01cce66` (`Handle unavailable evidence in issue projections`) was deployed to the active service checkout. The previous module is preserved at `/opt/gamota-research-mcp-oauth/src/gamota_research/reports.py.before-01cce66`; the deployed module SHA-256 is `f96e0f929de6a417c07f2ccd6d25527848bf7189930ad3b30cc3bf1431e21cbf`, matching the pushed commit. The file compiled with the service virtualenv's Python, and the service is active after restart.
- Post-patch public checks: `/` HTTP 200; `/reports/index.json` HTTP 200; unauthenticated `/mcp` HTTP 401; `/mcp-public` initialize HTTP 200; `tools/list` HTTP 200 with 18 tools. No report artifacts or Nginx configuration were changed.


## Final submission audit (2026-10-24)

- Current GitHub branch head: `0db3f05`; Mission 2 baseline `ae0d982` remains an ancestor in the same history.
- Fresh local verification on the submission tree: `uv run pytest -q` — **147 passed**; `cd web && npm run build` — **passed**; `git diff --check` — **passed**.
- Mission 2 evaluation cases remain in the full suite; current A1 tests include an assigned-conflict case, a missing-date edge case, and a supported-report regression case (see `mission3-a1.md`).
- Fresh hosted smoke: app `/` and `/reports/index.json` returned HTTP 200; `/mcp-public` initialized and listed 18 tools, including write/publish tools; the canonical mobile-games report remains in the five-entry public report index. `/mcp` remains authenticated.
- Final video artifact outside the repository: `gamota-mission3-demo-final-v4.mp4`, H.264/AAC, 1280×720, 25 fps, **200.704 seconds**. Full decode and keyframe inspection passed. Updated Vietnamese captions: `gamota-mission3-demo-final-v4.vi.srt`.
- The portal has the updated repository/demo links and all three revised answers saved as a draft. Its video URL field remains empty for the user's YouTube upload; the submission has not been finalized.
