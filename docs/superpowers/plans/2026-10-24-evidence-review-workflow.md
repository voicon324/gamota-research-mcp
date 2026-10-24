# Evidence Review Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make source assurance, freshness, evidence gaps, conflicts, and follow-up research clear in MCP guidance and every published report.

**Architecture:** Project already persisted source type/provenance and separate publication/observation dates. Add optional report projection fields, a reusable deterministic review projection for Markdown, and UI evidence review details plus issue-specific follow-up actions. No server-side source fetching or trust score.

**Tech Stack:** Python 3.13, pytest, TypeScript, React, Vite.

**Spec:** `docs/superpowers/specs/2026-10-24-evidence-review-workflow.md`

## Global Constraints

- Preserve report schema `1.0` and backward compatibility.
- Source URLs and quotes remain host-supplied and not independently verified by this service.
- Do not perform general web search or server-side source URL fetching.
- Mission 3 Change Request remains A1; A2–A5 are not simultaneous work items.

## Review Focus

- Missing publication date but recent observation remains freshness unknown.
- Old publication or observation date remains stale even if the other date is recent.
- No explicit cutoff is not silently labeled current.
- `UNKNOWN` or `DERIVED` provenance is surfaced as a review need without a false quality verdict.
- Legacy schema 1.0 reports without new fields continue to render.

## File map

- Modify `src/gamota_research/reports.py` to project optional source type/cutoff and render an evidence review block.
- Modify `src/gamota_research/mcp_server.py` to strengthen reusable agent workflow instructions.
- Modify `web/src/App.tsx` and `web/src/conflicts.css` to show source/freshness/assurance facts consistently and expose issue-specific follow-ups.
- Modify `tests/test_mission3_a1.py` and add a focused report projection test for freshness/provenance output.
- Update `docs/mission3-a1.md` and public setup/readme documentation after verification.

### Task 1: Report projection and Markdown evidence review

- [x] Add tests for projected freshness cutoff, source type, dated evidence review, unknown provenance, and legacy compatibility.
- [x] Run targeted tests and observe expected failures.
- [x] Project optional source type and freshness cutoff; render all known source/evidence facts and assurance boundaries in Markdown.
- [x] Run targeted tests.

### Task 2: Agent workflow and web review UI

- [x] Add report-projection regression coverage and type-check the issue/evidence follow-up input contract.
- [x] Strengthen MCP instructions for discovery, validation, uncertainty and same-chat summary.
- [x] Render freshness, provenance, source type, quote, locator, dates, confidence and exact link together for evidence items.
- [x] Let every open issue offer an appropriately scoped follow-up prompt; include source/date/provenance facts.
- [x] Run frontend production build.

### Task 3: Regression, deploy, and documentation

- [x] Run complete Python suite, frontend build, and `git diff --check`.
- [x] Deploy the branch to the configured host using the repository's deploy skill and verify reports/UI/MCP endpoints.
- [x] Update Mission 3 coverage/limits and deployment evidence without changing video or portal fields.
- [x] Record exact commands/results and any remaining limitations.
