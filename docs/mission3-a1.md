# Mission 3 — A1: conflicting sources

## Change and decision

Mission 2 already detected opposite signals and reduced confidence, but the published brief showed a generic open issue. A reviewer could not see which sources conflicted, what each source measured, or why the report stopped short of choosing a direction.

Mission 3 carries that validator result into the report and review UI. A comparable conflict is published as **ABSTAIN**, with the linked evidence IDs, direction, comparison signature, explanation, quoted evidence, measurement scope, dates, provenance and source links. When metric or scope differs, the result is **NOT_COMPARABLE** with the validator's reasons; it is not described as contradictory evidence. A copied follow-up prompt preserves the research question, run, market, platform, period, issue, evidence and URLs so Codex or Claude can continue with its own search tools.

The report remains schema `1.0`; Mission 3 fields are optional, preserving old report readers. The system does not rank sources with an invented trust score, pick a winner without evidence, or start another search automatically. The publishing agent still writes the executive verdict; the UI labels it separately from the deterministic directional assessment.

## Verification

`tests/test_mission3_a1.py` covers the assigned change request, a metric-scope edge case, malformed or missing references, legacy schema compatibility, a supported-report regression, and missing evidence. Results on this tree:

- `uv run pytest tests/test_mission3_a1.py -q` — **9 passed**.
- `uv run pytest -q` — **131 passed** at the current checkout, including the Mission 3, OAuth, and public MCP origin checks.
- `cd web && npm run build` — **passed** (TypeScript and Vite production build).
- `git diff --check` — **passed**.

The automated fixtures use `example.test` sources and synthetic evidence. A separate live end-to-end run was completed through the authenticated hosted MCP using original Sensor Tower and Unity report pages. It records a real-world pair of opposite-looking signals: Sensor Tower estimates global 2023 mobile-game consumer spend fell 2%, while Unity reports mobile DAU rose 4.1% in its measured cohort. The validator returned **NOT_COMPARABLE** because the metric and sampled population differ; it did not call this a source conflict or choose a winner. All three claims validated, both evidence slots were covered, and the COMPLETE run was published to the live report library. This demonstrates handling a real scope mismatch, not that the sources disagree on the same market outcome.

The system records URLs and provenance supplied by the host agent, but does not independently browse those URLs or prove that a quoted source is truthful. For this live run, the cited publisher pages and quoted passages were manually reopened and checked before publication.

## Required answers

### After the new request, what did you prioritize and what did you defer?

I prioritized making a conflict explainable and reviewable: show the two directions, compare their measurement scope, link each statement to its source, and abstain when comparable evidence disagrees. I deferred automated winner selection, a numeric source-trust score and automatic follow-up research because the product cannot justify those decisions from the stored evidence alone. Research remains in the connected host agent's native search tools.

### What changed most from Mission 2, and what evidence shows it is better?

The largest change is that a directional issue now changes the reader's decision view: it displays **ABSTAIN** for comparable opposite signals or **NOT_COMPARABLE** for mismatched scope, beside the exact evidence, dates, provenance and links. In Mission 2 the same issue was only a generic unknown. Evidence includes the targeted A1 suite (9 passed), the initial release regression suite (110 passed), and the current checkout regression suite (131 passed), production frontend build, authenticated MCP initialization and discovery of 18 tools, and the published live run above (COMPLETE, 3/3 valid claims, 2/2 evidence slots, one NOT_COMPARABLE issue). The live run demonstrates a real metric/sample mismatch; synthetic fixtures separately cover a true same-scope conflict.

### What is the largest remaining risk, and what would you do next?

The host agent can still misread a web page or enter an inaccurate quote or direction. The MCP checks structured links, scope and deterministic validation, but it does not independently fetch and verify the source. The live run was manually checked, but this remains a product risk. I would next add a source-verification step that reopens the cited location and compares its wording, date and scope with the recorded evidence, then test that across more real research sessions.

## Release evidence

The host's smoke returned `/` 200, unauthenticated and wrong-bearer `/mcp` 401, authenticated initialize PASS, and discovery of 18 tools. The live brief is `global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682` from run `7b5bf83a-5be3-4f7b-9b55-0a6a6e9e21ad`; its public JSON is available at `https://52.64.163.35/reports/global-mobile-games-market-2023-mobile-games-spending-and-activity-signals-7b5bf83a-67c10682/report.json`. The browser UI was refreshed and confirmed to show the report, source quotes, clickable citations and NOT_COMPARABLE explanation. Deployment checks are recorded in `docs/mission3-deployment-verification.md`.

## ChatGPT Web → MCP → public report demonstration

A separate ordinary-language ChatGPT Web session researched Honor of Kings' growth opportunity in Southeast Asia and asked Gamota Research to save the report. ChatGPT searched 41 pages, used the connected public MCP, received one-time approval for publication, and returned a report card and public URL in the same conversation. The published run is COMPLETE with 16 findings, 15 evidence records, 9 sources and 6 unknowns; confidence is MEDIUM. The validator returned NOT_COMPARABLE because the observations do not share a common metric and scope. The report recommends conditional market tests and explicitly says public evidence does not establish country-level DAU, retention, net IAP, CAC/LTV, or positive ROI.

- ChatGPT conversation: <https://chatgpt.com/c/6adb7c3c-81dc-83ec-a937-b0a59942905b>
- Published report: <https://52-64-163-35.sslip.io/?report=honor-of-kings-honor-of-kings-t-i-ng-nam-10-2026-c-h-i-t-ng-tr-ng-v-th-tr-ng-u-ti-n-68edfb56-bf5fac6a#published>
- Report ID: `honor-of-kings-honor-of-kings-t-i-ng-nam-10-2026-c-h-i-t-ng-tr-ng-v-th-tr-ng-u-ti-n-68edfb56-bf5fac6a`
- Research run: `68edfb56-d2b2-4273-b7f6-4be909cf4bd4`
- Current public index, report JSON and Markdown were fetched from the hosted service and returned HTTP 200; snapshots are in `evidence/mission3/chatgpt-web/`.
- The ChatGPT response and published report page were reopened in the signed-in browser and visually checked. Several reported sources were spot-checked independently; this was not an exhaustive audit of all nine sources.
