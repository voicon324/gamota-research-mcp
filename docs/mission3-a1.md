# Mission 3 — A1: conflicting sources

The Mission 2 submission baseline is commit `ae0d982` (`Complete Mission 2 submission package`). The A1 implementation was introduced in `01b2e1a` (`Improve conflict review for Mission 3 A1`) and preserved the original repository history.

## Change and decision

Mission 2 already detected opposite signals and reduced confidence, but the published brief showed a generic open issue. A reviewer could not see which sources conflicted, what each source measured, or why the report stopped short of choosing a direction.

Mission 3 carries that validator result into the report and review UI. A comparable conflict is published as **ABSTAIN**, with the linked evidence IDs, direction, comparison signature, explanation, quoted evidence, measurement scope, dates, provenance and source links. When metric or scope differs, the result is **NOT_COMPARABLE** with the validator's reasons; it is not described as contradictory evidence. A copied follow-up prompt preserves the research question, run, market, platform, period, issue, evidence and URLs so Codex or Claude can continue with its own search tools.

The report remains schema `1.0`; Mission 3 fields are optional, preserving old report readers. The system does not rank sources with an invented trust score, pick a winner without evidence, or start another search automatically. The publishing agent still writes the executive verdict; the UI labels it separately from the deterministic directional assessment.

### A1.1 follow-up: make source assurance explicit

The A1 review UI previously showed source links and quotations without making clear that both were supplied by the connected host agent. Published evidence now carries a server-generated `source_assurance` field with status `NOT_INDEPENDENTLY_VERIFIED`, URL and quote origin `HOST_SUPPLIED`, and `source_retrieved_by_server: false`. The report reader displays this as **Not independently verified** beside evidence. Caller metadata cannot set or override these reserved assurance fields, including in legacy database rows.

This label describes the MCP server's own actions; it does not assert that a source is false, low quality, or unverifiable. It does not prove that a host agent's quote matches the linked page. The MCP continues to validate recorded structure, scope, dates and claim/evidence relationships. Older reports without `source_assurance` remain valid and render without the label. Server-side URL retrieval is deferred until a separate security review and explicit approval; this increment makes no outbound source requests.

### Common requirement follow-up: freshness, grounding, and readable gaps

The Mission 3 common requirement also asks the reviewer to identify stale or missing evidence, verify what the system itself concluded, and see where more research is needed. This follow-up tightens those behaviors without changing the MCP API or report schema:

- Numeric grounding uses quoted text and the explicit structured value/unit fields. Numbers in arbitrary metadata no longer count as evidence for a claim.
- Source publication date and metric observation date are separate. A recent observation cannot make an old or undated source current; either known date before the freshness cutoff is stale, and missing either date is unknown.
- Markdown and web report readers place the deterministic system assessment and evidence gaps before the publishing agent's unverified verdict and findings. The report distinguishes the validator's outcome from the host agent's editorial conclusion.
- Follow-up research guidance is available for stale, undated, unsupported and missing evidence, alongside existing ABSTAIN and comparability cases. Deeper coverage can be guided by the existing lineage and evidence-slot audits; this change does not invent a cross-claim conflict detector.

Tests added first for forged numeric metadata, old publication with recent observation, missing publication date, prominent missing-slot disclosure, and system-versus-agent assessment ordering. On the updated tree, `uv run pytest -q` passes **138 tests**; `cd web && npm run build` passes. These results describe the local candidate until a new deployment verification is recorded below.

## Verification

At the original A1 release, `tests/test_mission3_a1.py` covered the assigned change request, a metric-scope edge case, malformed or missing references, legacy schema compatibility, a supported-report regression, and missing evidence. The follow-up adds a forged/legacy metadata edge case, a report projection check, and a regression check for traces without the optional field. Results on this tree:

- `uv run pytest tests/test_mission3_a1.py -q` — **9 passed at original A1 release**; the follow-up report tests are included in the full suite below.
- `uv run pytest -q` — **131 passed** at the original A1 release checkout, including the Mission 3, OAuth, and public MCP origin checks.
- `cd web && npm run build` — **passed** (TypeScript and Vite production build).
- `git diff --check` — **passed**.

### Final verification on 2026-10-24

Verified on the Mission 3 A1.1 release commit `d01f260`. Its technical branch point is `47ccfb2` (`Record final Mission 3 verification`); the Mission 2 submission baseline remains `ae0d982` (`Complete Mission 2 submission package`):

- `uv run pytest --collect-only -q tests/test_mission3_a1.py` — **11 tests collected**.
- `uv run pytest tests/test_mission3_a1.py -q` — **11 passed**.
- `uv run pytest -q` — **135 passed**, 0 failed, 0 skipped.
- `cd web && npm run build` — **passed** (TypeScript and Vite production build).
- Public app `/`, report index, and the published Honor of Kings report JSON — **HTTP 200** over the canonical HTTPS hostname.
- Public MCP `/mcp-public` — `initialize` **HTTP 200**, followed by `tools/list` with **18 tools**.
- The deployed JavaScript asset referenced by the public page contains the A1 `ABSTAIN`, `NOT_COMPARABLE`, and `directional_decision` review behavior. The deployed asset filename matched the successful local production build.
- A1.1 release deployed from commit `e2ca75c`: both MCP systemd services are active; homepage and report index return HTTP 200; `/mcp` rejects an unauthenticated initialize with HTTP 401; `/mcp-public` initializes and lists 18 tools. The live JavaScript asset is `index-DePCuX8t.js` and contains the “Not independently verified” label. Existing report artifacts remain unchanged; the optional label appears in reports published by the updated service.
- The live mobile-games report is a scope-mismatch example, with a published `NOT_COMPARABLE` directional assessment. It is not evidence of two sources disagreeing on the same metric and scope; same-scope `ABSTAIN` is demonstrated by the deterministic A1 fixture and is explicitly labeled synthetic in the demo.
- `gamota-mission3-demo-final-v2.mp4` — **165.653 seconds** (2m 45.653s), below the 5-minute limit. The revised narration states the current 11 targeted and 135 full-suite test counts; the research and report walkthrough remains the real ChatGPT Web → MCP run. The video and matching Vietnamese subtitles are prepared locally for the user's YouTube upload; the portal's YouTube field remains for the user to fill after upload.

Use the canonical HTTPS host `https://52-64-163-35.sslip.io/` for the app, MCP, and report links. The direct-IP URL `https://52.64.163.35/` fails TLS hostname validation in current clients.

The automated fixtures use `example.test` sources and synthetic evidence. A separate live end-to-end run was completed through the authenticated hosted MCP using original Sensor Tower and Unity report pages. It records a real-world pair of opposite-looking signals: Sensor Tower estimates global 2023 mobile-game consumer spend fell 2%, while Unity reports mobile DAU rose 4.1% in its measured cohort. The validator returned **NOT_COMPARABLE** because the metric and sampled population differ; it did not call this a source conflict or choose a winner. All three claims validated, both evidence slots were covered, and the COMPLETE run was published to the live report library. This demonstrates handling a real scope mismatch, not that the sources disagree on the same market outcome.

The system records URLs and provenance supplied by the host agent, but does not independently browse those URLs or prove that a quoted source is truthful. For this live run, the cited publisher pages and quoted passages were manually reopened and checked before publication. New reports now state that boundary on each evidence item; the manual spot-check is separate from MCP assurance.

## Required answers

### After the new request, what did you prioritize and what did you defer?

I prioritized making a conflict explainable and reviewable: show the two directions, compare their measurement scope, link each statement to its source, and abstain when comparable evidence disagrees. In the follow-up, I made the evidence boundary explicit by marking the URL and quotation as host-supplied and not independently retrieved by the MCP. I deferred automated winner selection, a numeric source-trust score, automatic follow-up research and server-side fetching because the stored evidence alone cannot justify them and retrieval needs a separate security review.

### What changed most from Mission 2, and what evidence shows it is better?

The largest change from Mission 2 is that a directional issue now changes the reader's decision view: it displays **ABSTAIN** for comparable opposite signals or **NOT_COMPARABLE** for mismatched scope, beside the evidence and source links. The follow-up adds an explicit not-independently-verified label for host-supplied quotes and URLs. Evidence includes the A1 regression suite, new tests for reserved metadata and old report compatibility, the current full suite (**135 passed**), a successful production frontend build, the deployed live asset, active MCP services, unauthenticated public MCP initialization and discovery of 18 tools, and the published live run above (COMPLETE, 3/3 valid claims, 2/2 evidence slots, one NOT_COMPARABLE issue). The live run demonstrates a real metric/sample mismatch; synthetic fixtures separately cover a true same-scope conflict. Existing report artifacts are preserved and do not receive the new optional field retroactively.

### What is the largest remaining risk, and what would you do next?

The host agent can still misread a web page or enter an inaccurate quote or direction. The UI now discloses that the MCP did not independently retrieve the source, but users still need to open links and validate important claims. Next I would design a separately reviewed retrieval service with domain controls, network-egress safeguards, page and citation parsing, and measurable quotation/date/scope checks, then evaluate it on real research sessions before enabling it.

## Release evidence

The live brief is `global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682` from run `7b5bf83a-5be3-4f7b-9b55-0a6a6e9e21ad`; its public JSON is available at [`report.json`](https://52-64-163-35.sslip.io/reports/global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682/report.json), and its [review page](https://52-64-163-35.sslip.io/?report=global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682#published) opens in the web app. The browser UI was refreshed and confirmed to show the report, source quotes, clickable citations and NOT_COMPARABLE explanation. Deployment checks are recorded in `docs/mission3-deployment-verification.md`.

## ChatGPT Web → MCP → public report demonstration

A separate ordinary-language ChatGPT Web session researched Honor of Kings' growth opportunity in Southeast Asia and asked Gamota Research to save the report. ChatGPT's visible research trace records searches of 41 pages and a later 12-page search; it returned the published report card and public URL in the same conversation. The published run is COMPLETE with 16 findings, 15 evidence records, 9 sources and 6 unknowns; confidence is MEDIUM. The validator returned NOT_COMPARABLE because the observations do not share a common metric and scope. The report recommends conditional market tests and explicitly says public evidence does not establish country-level DAU, retention, net IAP, CAC/LTV, or positive ROI.

- ChatGPT conversation: <https://chatgpt.com/c/6adb7c3c-81dc-83ec-a937-b0a59942905b>
- Published report: <https://52-64-163-35.sslip.io/?report=honor-of-kings-honor-of-kings-t-i-ng-nam-10-2026-c-h-i-t-ng-tr-ng-v-th-tr-ng-u-ti-n-68edfb56-bf5fac6a#published>
- Report ID: `honor-of-kings-honor-of-kings-t-i-ng-nam-10-2026-c-h-i-t-ng-tr-ng-v-th-tr-ng-u-ti-n-68edfb56-bf5fac6a`
- Research run: `68edfb56-d2b2-4273-b7f6-4be909cf4bd4`
- Current public index, report JSON and Markdown were fetched from the hosted service and returned HTTP 200; snapshots are in `evidence/mission3/chatgpt-web/`.
- The ChatGPT response and published report page were reopened in the signed-in browser and visually checked. Several reported sources were spot-checked independently; this was not an exhaustive audit of all nine sources.
- Fresh ChatGPT and public-report captures are in `evidence/mission3/demo-stills/honor-*.jpg`. They are authentic screenshots animated with zoom/pan in the local video `gamota-mission3-demo-final-v2.mp4`; the video itself is delivered outside this repository. The video URL field on the Mission 3 portal is intentionally left blank for the user's YouTube upload.
