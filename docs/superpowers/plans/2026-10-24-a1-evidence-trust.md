# Mission 3 A1.1 Evidence Trust Transparency Implementation Plan

> **For agentic workers:** execute inline with TDD; preserve the Mission 2 history and existing A1 decisions.

**Goal:** Show report readers and connected host agents that source URLs and quotes are host-supplied and were not independently fetched by the MCP server.

**Architecture:** Derive a server-owned assurance object at trace/report projection time. Strip reserved assurance keys from untrusted metadata before it can be surfaced. Add the object as an optional property on report evidence and render it conditionally in the web UI. No HTTP retrieval, migration, or report schema version change.

**Tech Stack:** Python 3.13, SQLite metadata JSON, pytest, React, TypeScript, Vite.

**Spec:** `docs/superpowers/specs/2026-10-24-a1-evidence-trust.md`

## Global Constraints

- Do not modify the Mission 2 commit history or the two unrelated pre-existing untracked paths in the original checkout.
- No server-side network retrieval; no outbound HTTP call may be introduced.
- Do not accept caller-provided assurance as trusted.
- Preserve existing MCP signatures, report envelope, schema version, and A1 decisions.
- Omit optional assurance on old reports; render them without error or a false verification badge.
- Add at least three tests: A1 behavior regression, forged/legacy metadata edge case, and report/UI projection behavior.

## Review Focus

- A caller forges `VERIFIED` in evidence metadata; API/report must not surface it as authoritative.
- Legacy database metadata contains a reserved key from an earlier version; trace output must filter it.
- Old report JSON has no assurance property; current UI must remain renderable and show no verified badge.
- Report generation copies only the explicit server assurance fields, never arbitrary evidence metadata.
- Source assurance must not alter `ABSTAIN` or `NOT_COMPARABLE` outcomes.

---

### Task 1: Server-owned assurance and metadata boundary

**Files:**
- Create: `src/gamota_research/source_assurance.py`
- Modify: `src/gamota_research/repository.py`
- Test: `tests/test_source_assurance.py`
- Test: `tests/test_mission3_a1.py`

**Interfaces:**
- Produce `source_assurance_for_host_supplied_source() -> dict[str, object]` with fixed status/origin/retrieval fields and explanatory text.
- Produce `sanitize_untrusted_metadata(metadata: dict[str, object]) -> dict[str, object]` that removes reserved `source_assurance` and `source_verification` keys.
- `Repository.get_claim_trace` adds top-level `source_assurance` to each evidence item and sanitizes evidence and source metadata. It must not claim retrieval or verification.

- [ ] Write tests for forged metadata filtering, SQLite round-trip, assurance fields, and unchanged A1 status.
- [ ] Run targeted tests and confirm they fail for the missing behavior.
- [ ] Implement the small assurance helper and repository projection/filtering.
- [ ] Run targeted tests and confirm they pass.
- [ ] Commit the verified server-owned assurance boundary.

### Task 2: Backward-compatible report projection and UI

**Files:**
- Modify: `src/gamota_research/reports.py`
- Modify: `web/src/App.tsx`
- Modify: `web/src/conflicts.css` or the evidence presentation stylesheet actually used by the report view.
- Test: `tests/test_source_assurance.py`

**Interfaces:**
- New report evidence may include optional `source_assurance`; copy only the server-generated object from `get_claim_trace`.
- TypeScript evidence has optional `source_assurance` with literal trust fields.
- UI conditionally shows “Not independently verified” and explanatory source-origin text; no green success state. Older report objects without the field remain accepted.

- [ ] Add report projection tests proving only assurance fields are exposed and old output omits the optional property.
- [ ] Run the report tests and confirm they fail before implementation.
- [ ] Implement optional projection and conditional UI rendering.
- [ ] Run report tests and web build; confirm both pass.
- [ ] Commit the verified report/UI projection.

### Task 3: Document behavior and verify regression

**Files:**
- Modify: `docs/mission3-a1.md`
- Modify: `README.md` only if its current workflow description would otherwise imply independent source verification.
- Test: `tests/test_source_assurance.py`, `tests/test_mission3_a1.py`

- [ ] Add the required edge and regression tests for old metadata, old reports, and A1 outcomes.
- [ ] Document what the label means, what it does not prove, and that live retrieval is deferred pending explicit approval/security review.
- [ ] Run `uv run pytest -q`, `cd web && npm run build`, and `git diff --check`.
- [ ] Inspect Git status and confirm the two unrelated pre-existing untracked paths in the original checkout were not changed.
- [ ] Commit the documentation and final regression evidence.
