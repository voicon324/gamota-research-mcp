# Mission 2 Evidence Map

> **Official rubric verified:** 2026-10-15 from the authenticated `portal.agentlize.dev/mission/2` page. Research, Codex fixture-smoke and local HTTP smoke evidence is recorded; online deployment, GitHub publication, presentation video and owner-provided Mission 1 rationale remain open.

## Executive result

The technical MVP evidence currently covers the implementation and gates listed below. Canonical real-web research artifacts R1 and R2 now cover two distinct questions. The standout system behavior is that it preserves source lineage and refuses to turn incompatible platform/time/definition figures into an unsupported benchmark. The separate deterministic lineage demonstration shows that **three citations can represent only one independent evidentiary root**. The official rubric also requires an evaluation report in a specific format, three written answers, an AI usage log, a public repository, an online demo or reason for not deploying, and a short presentation. Remaining items are tracked below and in `mission2-evaluation-report.md`.

The official rubric has been read and reconciled. H2 remains open for submission artifacts and owner-provided Mission 1 context; a Codex-host fixture smoke and two actual research runs are recorded.

## Requirement-to-evidence map

| Established requirement | Implementation | Deterministic test/eval | Runtime or demo evidence | Status |
|---|---|---|---|---|
| Installable Python MCP server with persistent research state | `pyproject.toml`; `src/gamota_research/mcp_server.py`; `src/gamota_research/db.py`; `src/gamota_research/repository.py` | `tests/test_research_run.py`; `tests/test_research_contract.py`; `tests/test_mcp_stdio.py` | Final wheel and isolated install were previously verified; Codex-host smoke persisted and re-read a run through a separate host process | J1–J4 passed on the recorded baseline; final-tree rerun remains |
| 15-tool MCP surface for research lifecycle, trace/lineage and game/store domain operations | `src/gamota_research/mcp_tools.py`; `src/gamota_research/mcp_server.py` | `tests/test_mcp_protocol.py`; `tests/test_store_mcp.py`; `tests/test_mcp_stdio.py` | Direct wheel and Codex-host smokes listed the expected 15 tools and made successful calls in dedicated databases | J1–J4 passed on the recorded baseline; final-tree rerun remains |
| Persist a bounded research contract, progress counters, evidence slots and explicit stop reasons | `src/gamota_research/contract.py`; `src/gamota_research/mcp_tools.py`; `src/gamota_research/validator.py` | `tests/test_research_contract.py`; `tests/test_research_budget.py`; `tests/test_stop_conditions.py` | Gate F: 5/6 host searches, 2/2 rounds, 0/20 domain calls, all 3 required slots covered, within budget | Covered in Gate F |
| Ground claims in traceable evidence and expose claim/source lineage | `src/gamota_research/mcp_tools.py`; `src/gamota_research/provenance.py`; `src/gamota_research/repository.py` | `tests/test_evidence_traceability.py`; `tests/test_provenance_independence.py`; `tests/test_confidence_lineage.py` | Gate F: one `VALID / STRONG` claim with 2 evidence items and 2 roots. Gate G: one claim with 3 evidence items and 3 direct documents | Covered by F and G |
| Reject unsupported or numerically ungrounded claims; respect metric compatibility | `src/gamota_research/validator.py` | `tests/test_numeric_grounding.py`; `tests/test_claim_metric_compatibility.py`; `tests/evals/test_numeric_hallucination.py` | The pre-HTTP wheel passed 94 tests; current HTTP-enabled working tree passes 97 tests and 8 evals | Verified by current-tree suite; wheel evidence is historical |
| Represent stale evidence, missing evidence and research limitations explicitly | `src/gamota_research/validator.py`; `src/gamota_research/contract.py` | `tests/test_freshness.py`; `tests/test_stop_conditions.py`; `tests/evals/test_stale_evidence.py` | R2 keeps the exact first-30-day mobile revenue slot missing and returns PARTIAL/WEAK with the expected major GAP; the suite asserts missing required slots create a blocking GAP | Demonstrated by R2 and stop-condition test |
| Compare only evidence with compatible metric, market, unit, period and scope; surface conflicts | `src/gamota_research/comparability.py`; `src/gamota_research/validator.py` | `tests/test_comparability.py`; `tests/test_conflict.py`; `tests/evals/test_conflicting_evidence.py` | Current suite passed 97/97, including comparability and conflict scenarios | Verified by current-tree suite |
| Determine corroboration and confidence from independent provenance roots | `src/gamota_research/provenance.py`; `src/gamota_research/confidence.py`; `src/gamota_research/validator.py` | `tests/test_provenance_independence.py`; `tests/test_confidence_lineage.py`; `tests/evals/test_shared_origin.py` | Gate G run `b9c1b597-d8e1-497a-ba73-e48edaa51456`: 3 documents, 3 supporting citations, 1 independent root; `VALID / MODERATE`; `SHARED_ORIGIN` informational issue | Demonstrated |
| Keep fixture store data distinct from live observations and avoid unsupported market inferences | `src/gamota_research/domain/fixture_provider.py`; `src/gamota_research/domain/apple_rss_provider.py`; `src/gamota_research/domain/store_service.py` | `tests/test_store_provider.py`; `tests/test_store_semantics.py`; `tests/test_apple_rss_provider.py`; `tests/evals/test_store_rank_guardrail.py` | Codex fixture smoke finalized a synthetic run, verified trace/lineage and persistence after a new host process; R1/R2 used zero domain/store calls | Host integration demonstrated; HTTP-enabled suite now passes 97/97 |
| Host agent performs native web research; MCP records, checks and traces its results | `src/gamota_research/mcp_tools.py` tool descriptions; `docs/mission2-runbook.md` | `tests/test_research_budget.py`; `tests/test_mcp_protocol.py` | Canonical R1 and R2 are native-search runs with 3 and 5 queries, zero domain calls; artifacts contain claim traces and bounded conclusions | Demonstrated by R1/R2 artifacts |
| Validation-only assessment must not persist; finalization uses an explicit reason | `src/gamota_research/mcp_tools.py`; `src/gamota_research/validator.py` | `tests/test_mcp_protocol.py::test_mcp_validate_only_returns_finalization_assessment_without_writes`; `tests/test_stop_conditions.py` | Gate F validate-only hash unchanged before real finalize; actual finalize/readback then changed the DB hash as expected. Gate G validate-only hash unchanged before conditional finalize | Demonstrated in F and G |
| Connect Codex to the installed package and successfully call MCP tools | `config/codex-mcp.example.toml`; `tests/manual/codex_host_smoke.md`; `docs/mission2-runbook.md` | `tests/test_mcp_stdio.py` verifies stdio protocol, but does not replace host evidence | Codex host discovered 15 tools, completed a synthetic fixture run and read finalized run/trace/lineage after reconnecting with a new host process | Stdio J4 demonstrated; authenticated local HTTP initialize/tool discovery also passed |

## Gate F — live host-native research

- Run: `81229fe7-f9f5-4897-8c55-be6482326cd3`
- Final state: `COMPLETE`, `COVERAGE_SUFFICIENT`, confidence `STRONG`
- Claim: `738ca916-0f42-4502-9c40-76f27bf65b79`, `VALID / STRONG`, target metric `open_beta_start_date`
- Evidence: two `SUPPORTS` records from VLPlay and GameHub; two independent roots
- Progress: 5/6 host-reported searches, 2/2 research rounds, 0/20 domain calls; within budget
- Required slots: recent-release signal, independent cross-check and limitation check covered
- Integrity: final DB SHA-256 `247b6ad16fe58c3cc110023630a529e90ea9b426f41519151a082c3f7d710580`
- Recorded DB: `/tmp/gamota-research-gate-f-20261015.sqlite3`

The live-search capability came from the host agent. The MCP server persisted the research records and performed deterministic validation; it did not itself search the web.

## Gate G — Evidence Lineage Audit demonstration

- Run: `b9c1b597-d8e1-497a-ba73-e48edaa51456`
- Claim: `e62aba02-97ce-4094-a0f3-b462ce74408a`, `VALID / MODERATE`
- Three synthetic documents form the chain A → B → C; all resolve to root A.
- Three `SUPPORTS` evidence links point to three direct source records, but the lineage audit reports exactly **one independent root** and `SHARED_ORIGIN` as informational.
- Final state: `COMPLETE`, `COVERAGE_SUFFICIENT`
- Integrity: final DB SHA-256 `8fa0c1080dd8a7e35a066a99aa11a700060def25b91cb91705902f3a7b23bdc4`
- Recorded DB: `/tmp/gamota-research-gate-g-lineage-20261015.sqlite3`

This is a deterministic synthetic demonstration, separate from Gate F's live research database. It must not be presented as a live market finding.

## J1–J3 — technical preflight

- Fresh locked, non-editable Python 3.13.11 environment: `/tmp/gamota-research-mission2-final-env-20261015`
- Full suite from the checkout at that baseline: **94 passed** (pre-HTTP)
- Wheel: `/tmp/gamota-research-mission2-final-dist-20261015/gamota_research_mcp-0.1.0-py3-none-any.whl`
- Wheel SHA-256: `d56357736511dc10217e41a5aa9260138d41f8681ac763fcd41ea24bf422eb36`; required store fixture is present
- Full suite with the installed pre-HTTP wheel and copied tests outside the checkout: **94 passed**
- Direct MCP smoke DB: `/tmp/gamota-research-mission2-final-direct-smoke.sqlite3`
- Direct MCP: exactly 15 tools; `existing_claim_id` and `validate_only` present; `stop_reason` optional in the schema; `create_research_run` succeeded and `get_research_run` read it back
- Smoke run: `234ec8f0-0d60-4ce7-ae90-dbf4b764f24a`, status `CREATED`
- Direct smoke DB SHA-256: `65fd9e50e7cdabbee3ba685aad0b888e140d242c631f2a98f47bc0620075ab64`

Post-HTTP verification (2026-10-15): wheel SHA-256 `2381cb8774c829341881dc05261fb23e0539c08dce8eee106856e24e96c60a62` was installed in a clean Python 3.13.11 environment; copied tests passed **97/97** and **8/8 evals**. The local deployment-helper smoke returned `401` without a token, `401` with a wrong bearer, authenticated MCP initialize and 15 tools; a separate authenticated smoke created a run and read it back. The old wheel counts above describe the pre-HTTP revision only.

## Official Mission 2 rubric reconciliation (H2)

The portal rubric requires a prototype that demonstrates the most important solution slice; a core loop from research question through information sources to a grounded, verifiable conclusion; more than one question; source-quality differentiation; explicit missing/uncertain data; and a quality-testing method. It also requires at least five scenarios, including a good case, a hard/unclear-data case and a weak/failure case. Each scenario must report **Expected → Actual → Pass/Fail → Learning**.

The submission must answer three questions: (Q1) what the MVP chose to implement and why it demonstrates feasibility; (Q2) what changed from Mission 1 and what evidence caused the change; and (Q3) what the MVP handles poorly, why, and what to improve next. It must also disclose AI prompts/tools/decisions in an Evidence Log, provide a public GitHub repository with README and no secrets, provide an online demo if available or explain why not and give README local-run instructions, and provide a video no longer than five minutes covering problem → chosen proof → demo → hard case → limitation.

| Official criterion | Current status | Evidence / remaining proof |
|---|---|---|
| Selected MVP slice and feasibility rationale | NEEDS DEMO EVIDENCE | Implementation and Gate F/G pointers above; Q1 draft is in README. Need an evaluator-facing actual run showing why the slice proves feasibility. |
| End-to-end question → research → sources → grounded conclusion → user-verifiable evidence | PASS — R1/R2 artifacts | Two current readable artifacts preserve URLs, quotes, claims, traces and validator output. |
| More than one research question handled | PASS — R1 and R2 | R1 and R2 are distinct live web-research runs with separate contracts, databases and artifacts. |
| Important conclusions grounded in specific evidence | PASS — R1/R2 traces | R1 has 4 VALID claims with complete coverage; R2 has 7 VALID claims and an explicit missing required slot. |
| Source reliability/provenance differentiated | PASS — research artifacts and Gate G | R1 distinguishes primary DeNA releases from trade-press corroboration; R2 records underlying estimators, source quality and shared publisher lineage. Gate G remains synthetic and labeled as such. |
| Missing, conflicting or uncertain information represented | PASS — R2 | Exact first-30-day slot remains missing; MISSING_EVIDENCE warning plus expected major GAP produce PARTIAL/WEAK rather than an unsupported COMPLETE result. |
| Quality evaluation exists | PASS — implementation and research trials | Eight executable behavioral evaluations plus two actual end-to-end research cases are inventoried. Current HTTP-enabled tree passed 97 tests and 8 evals; rerun after any further source changes. |
| At least five evaluation scenarios | PASS — coverage | Eight scenarios inventoried in `docs/mission2-evaluation-report.md`. |
| Good, hard/unclear and weak/failure scenarios represented | PASS — scenario coverage | Automated cases cover ambiguity, conflict, numeric/source failures and stale data; R1 is the real good case and R2 is the real missing/conflicting case. |
| Each case has Expected → Actual → Pass/Fail → Learning | PASS — evaluation report | Eight executable cases and two real research trials each have the required fields. |
| Q1 selected slice and feasibility | DRAFT | README Q1 draft; owner review remains. |
| Q2 Mission 1 decision change and trigger | GAP — owner input | Requires the actual Mission 1 decision and evidence that changed it. No inference made. |
| Q3 limitation, cause and next priority | PARTIAL | R2 demonstrates the limitation: numeric token validation is strict and required evidence gaps force PARTIAL. Further improvement priority is robust date/amount normalization and deployed HTTP transport, without weakening validation. |
| AI Evidence Log | PARTIAL | `docs/ai-evidence-log.md` records known tools/tasks and marks unknowns. Owner verification is pending where noted. |
| README, local setup and Codex path | PARTIAL | Local stdio quickstart and host setup are documented; final online HTTP client steps and rehearsal remain. |
| Online demo or no-deploy reason plus local instructions | GAP — deployment | User authorized AITC deployment. HTTP transport and local auth smoke pass; human installation, public route and remote MCP smoke are still needed. |
| Public GitHub repository | GAP — publication | Local project repository exists; GitHub remote has not yet been created or pushed. User asked for browser-based creation. |
| No API key/password/sensitive data in public material | PARTIAL — local audit | Filename and content-pattern scan of current repo files found no key/env/database candidates or credential-shaped values; manually review findings before public push and verify the remote tree afterward. |
| ≤5-minute presentation covering required flow | GAP | Remotion video is planned after deployment and final report; no rendered artifact yet. |
| Submission through HR/Gamota | NOT APPLICABLE at H2 | Check during final pre-submit audit; no submission was made. |

H2 remains **GAP** until the remaining owner-dependent answer and submission artifacts are resolved. The two research runs are complete; the remaining sequence is final-tree verification, HTTP transport/deployment, GitHub publication, remote smoke and Remotion video. The exact Mission 1 scope-change rationale remains unverified and is not inferred. The detailed case inventory is in `docs/mission2-evaluation-report.md`; AI usage is in `docs/ai-evidence-log.md`.

## Remaining verification

| Gate | Remaining evidence |
|---|---|
| H1 | Official requirements mapped to current repository evidence |
| H2 | Official rubric read; R1/R2 and case results recorded; AITC deployment, public repository, video and owner-provided Q2 remain |
| I | Reproducible stdio runbook and AITC HTTP deployment handoff are in `docs/mission2-runbook.md` and `deploy/README_DEPLOY.md` |
| J1–J3 | Pre-HTTP locked environment/wheel checks passed at 94 tests; the post-HTTP wheel was installed in a clean environment and passed 97/97 tests and 8/8 evals. Local HTTP verification covered no/wrong-token 401, authenticated initialize, 15-tool discovery and a separate authenticated create/readback smoke. |
| J4–J5 | Codex fixture smoke/reconnect and real R1/R2 artifacts are recorded; authenticated HTTP local smoke passes; remote deployment smoke and final integrity/status audit remain |

Do not mark H, J or the overall mission complete until every mandatory rubric item has evidence, H2 is GREEN, and the final J checks pass.
