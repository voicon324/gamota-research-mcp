# Mission 3 — A1: conflicting sources

## Change and decision

Mission 2 already detected opposite signals and reduced confidence, but the published brief showed a generic open issue. A reviewer could not see which sources conflicted, what each source measured, or why the report stopped short of choosing a direction.

Mission 3 carries that validator result into the report and review UI. A comparable conflict is published as **ABSTAIN**, with the linked evidence IDs, direction, comparison signature, explanation, quoted evidence, measurement scope, dates, provenance and source links. When metric or scope differs, the result is **NOT_COMPARABLE** with the validator's reasons; it is not described as contradictory evidence. A copied follow-up prompt preserves the research question, run, market, platform, period, issue, evidence and URLs so Codex or Claude can continue with its own search tools.

The report remains schema `1.0`; Mission 3 fields are optional, preserving old report readers. The system does not rank sources with an invented trust score, pick a winner without evidence, or start another search automatically. The publishing agent still writes the executive verdict; the UI labels it separately from the deterministic directional assessment.

## Verification

`tests/test_mission3_a1.py` covers the assigned change request, a metric-scope edge case, malformed or missing references, legacy schema compatibility, a supported-report regression, and missing evidence. Results on this tree:

- `uv run pytest tests/test_mission3_a1.py -q` — **9 passed**.
- `uv run pytest -q` — **110 passed**.
- `cd web && npm run build` — **passed** (TypeScript and Vite production build).
- `git diff --check` — **passed**.

The fixtures use `example.test` sources and synthetic evidence. They verify the report behavior; they are not real game-market findings. The system records URLs and provenance supplied by the host agent, but does not independently browse those URLs or prove that a quoted source is truthful.

## Required answers

### After the new request, what did you prioritize and what did you defer?

I prioritized making a conflict explainable and reviewable: show the two directions, compare their measurement scope, link each statement to its source, and abstain when comparable evidence disagrees. I deferred automated winner selection, a numeric source-trust score and automatic follow-up research because the product cannot justify those decisions from the stored evidence alone. Research remains in the connected host agent's native search tools.

### What changed most from Mission 2, and what evidence shows it is better?

The largest change is that a conflict now changes the reader's decision view: it displays **ABSTAIN** (or **NOT_COMPARABLE** for scope mismatch) beside the exact evidence, dates, provenance and links. In Mission 2 the same issue was only a generic unknown. Evidence is the targeted A1 suite, including conflict, scope mismatch, invalid-reference, legacy-report and missing-evidence cases, plus the full regression suite and production frontend smoke checks. Tests use synthetic fixtures, so they prove behavior, not market truth.

### What is the largest remaining risk, and what would you do next?

The host agent can still misread a web page or enter an inaccurate quote or direction. The MCP checks structured links, scope and deterministic validation, but it does not independently fetch and verify the source. Next I would add a source-verification step that reopens the cited location and compares its wording and date with the recorded evidence, then run an end-to-end research session through Codex or Claude against real sources.

## Release evidence

The host's pre-release smoke returned `/` 200, unauthenticated `/mcp` 401 and `/reports/index.json` 200; Nginx and the MCP service were active. The static frontend release and post-release checks are recorded in `docs/mission3-deployment-verification.md`. These checks do not prove a live, agent-authored conflict report: the A1 cases above use synthetic test evidence.
