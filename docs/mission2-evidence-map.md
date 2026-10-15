# Mission 2 Evidence Map

> **Official rubric verified:** 2026-10-15 from the authenticated `portal.agentlize.dev/mission/2` page. H2 is still **GAP**: this map now includes the official requirements, but several submission/evaluation artifacts and live demonstrations remain incomplete. This status is not a completion claim.

## Executive result

The technical MVP evidence currently covers the implementation and gates listed below. Gate F is a completed live host-native research run; Gate G is a separate deterministic lineage demonstration. The standout result is that **three citations can represent only one independent evidentiary root**. Provenance lineage, rather than citation count, determines independence. The official rubric also requires multiple question scenarios, an evaluation report in a specific format, three written answers, an AI usage log, a public repository, a demo/local-running path, and a short presentation. The current state of those items is recorded below and in `mission2-evaluation-report.md`.

H1 is provisional; H2, the final real Codex smoke, and the final mission certification remain pending official rubric access.

## Requirement-to-evidence map

| Established requirement | Implementation | Deterministic test/eval | Runtime or demo evidence | Status |
|---|---|---|---|---|
| Installable Python MCP server with persistent research state | `pyproject.toml`; `src/gamota_research/mcp_server.py`; `src/gamota_research/db.py`; `src/gamota_research/repository.py` | `tests/test_research_run.py`; `tests/test_research_contract.py`; `tests/test_mcp_stdio.py` | Final wheel built; all 94 tests passed from the checkout and from a copied test tree using the installed wheel | J1–J3 technical preflight passed; Codex host verification pending |
| 15-tool MCP surface for research lifecycle, trace/lineage and game/store domain operations | `src/gamota_research/mcp_tools.py`; `src/gamota_research/mcp_server.py` | `tests/test_mcp_protocol.py`; `tests/test_store_mcp.py`; `tests/test_mcp_stdio.py` | Final direct wheel smoke listed exactly 15 tools, inspected final schemas, created and read back a run in a dedicated DB | Direct preflight passed; real Codex smoke pending |
| Persist a bounded research contract, progress counters, evidence slots and explicit stop reasons | `src/gamota_research/contract.py`; `src/gamota_research/mcp_tools.py`; `src/gamota_research/validator.py` | `tests/test_research_contract.py`; `tests/test_research_budget.py`; `tests/test_stop_conditions.py` | Gate F: 5/6 host searches, 2/2 rounds, 0/20 domain calls, all 3 required slots covered, within budget | Covered in Gate F |
| Ground claims in traceable evidence and expose claim/source lineage | `src/gamota_research/mcp_tools.py`; `src/gamota_research/provenance.py`; `src/gamota_research/repository.py` | `tests/test_evidence_traceability.py`; `tests/test_provenance_independence.py`; `tests/test_confidence_lineage.py` | Gate F: one `VALID / STRONG` claim with 2 evidence items and 2 roots. Gate G: one claim with 3 evidence items and 3 direct documents | Covered by F and G |
| Reject unsupported or numerically ungrounded claims; respect metric compatibility | `src/gamota_research/validator.py` | `tests/test_numeric_grounding.py`; `tests/test_claim_metric_compatibility.py`; `tests/evals/test_numeric_hallucination.py` | 94/94 tests passed in the fresh locked environment and against the installed wheel | Verified by final suite |
| Represent stale evidence, missing evidence and research limitations explicitly | `src/gamota_research/validator.py`; `src/gamota_research/contract.py` | `tests/test_freshness.py`; `tests/test_stop_conditions.py`; `tests/evals/test_stale_evidence.py` | Gate F covered the required limitation slot and returned no blocking issues; final suite passed 94/94 | Verified by F and final suite |
| Compare only evidence with compatible metric, market, unit, period and scope; surface conflicts | `src/gamota_research/comparability.py`; `src/gamota_research/validator.py` | `tests/test_comparability.py`; `tests/test_conflict.py`; `tests/evals/test_conflicting_evidence.py` | Final suite passed 94/94, including comparability and conflict scenarios | Verified by final suite |
| Determine corroboration and confidence from independent provenance roots | `src/gamota_research/provenance.py`; `src/gamota_research/confidence.py`; `src/gamota_research/validator.py` | `tests/test_provenance_independence.py`; `tests/test_confidence_lineage.py`; `tests/evals/test_shared_origin.py` | Gate G run `b9c1b597-d8e1-497a-ba73-e48edaa51456`: 3 documents, 3 supporting citations, 1 independent root; `VALID / MODERATE`; `SHARED_ORIGIN` informational issue | Demonstrated |
| Keep fixture store data distinct from live observations and avoid unsupported market inferences | `src/gamota_research/domain/fixture_provider.py`; `src/gamota_research/domain/apple_rss_provider.py`; `src/gamota_research/domain/store_service.py` | `tests/test_store_provider.py`; `tests/test_store_semantics.py`; `tests/test_apple_rss_provider.py`; `tests/evals/test_store_rank_guardrail.py` | 94/94 tests passed; Codex fixture smoke procedure is in `tests/manual/codex_host_smoke.md` | Deterministic suite verified; host smoke pending |
| Host agent performs native web research; MCP records, checks and traces its results | `src/gamota_research/mcp_tools.py` tool descriptions; `docs/mission2-runbook.md` | `tests/test_research_budget.py`; `tests/test_mcp_protocol.py` | Gate F was the live host-native research trial: run `81229fe7-f9f5-4897-8c55-be6482326cd3`, `COMPLETE / STRONG`, `COVERAGE_SUFFICIENT`, 5/6 searches, 2/2 rounds, 2 independent roots | Demonstrated in Gate F |
| Validation-only assessment must not persist; finalization uses an explicit reason | `src/gamota_research/mcp_tools.py`; `src/gamota_research/validator.py` | `tests/test_mcp_protocol.py::test_mcp_validate_only_returns_finalization_assessment_without_writes`; `tests/test_stop_conditions.py` | Gate F validate-only hash unchanged before real finalize; actual finalize/readback then changed the DB hash as expected. Gate G validate-only hash unchanged before conditional finalize | Demonstrated in F and G |
| Connect Codex to the installed package and successfully call MCP tools | `config/codex-mcp.example.toml`; `tests/manual/codex_host_smoke.md`; `docs/mission2-runbook.md` | `tests/test_mcp_stdio.py` verifies stdio protocol, but does not replace host evidence | Direct smoke verified the wheel and schemas; final Codex-host smoke must show exactly 15 tools and a successful call in its own DB | Pending final J4 after H2 |

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
- Full suite from the checkout: **94 passed**
- Wheel: `/tmp/gamota-research-mission2-final-dist-20261015/gamota_research_mcp-0.1.0-py3-none-any.whl`
- Wheel SHA-256: `d56357736511dc10217e41a5aa9260138d41f8681ac763fcd41ea24bf422eb36`; required store fixture is present
- Full suite with the installed wheel and copied tests outside the checkout: **94 passed**
- Direct MCP smoke DB: `/tmp/gamota-research-mission2-final-direct-smoke.sqlite3`
- Direct MCP: exactly 15 tools; `existing_claim_id` and `validate_only` present; `stop_reason` optional in the schema; `create_research_run` succeeded and `get_research_run` read it back
- Smoke run: `234ec8f0-0d60-4ce7-ae90-dbf4b764f24a`, status `CREATED`
- Direct smoke DB SHA-256: `65fd9e50e7cdabbee3ba685aad0b888e140d242c631f2a98f47bc0620075ab64`

## Official Mission 2 rubric reconciliation (H2)

The portal rubric requires a prototype that demonstrates the most important solution slice; a core loop from research question through information sources to a grounded, verifiable conclusion; more than one question; source-quality differentiation; explicit missing/uncertain data; and a quality-testing method. It also requires at least five scenarios, including a good case, a hard/unclear-data case and a weak/failure case. Each scenario must report **Expected → Actual → Pass/Fail → Learning**.

The submission must answer three questions: (Q1) what the MVP chose to implement and why it demonstrates feasibility; (Q2) what changed from Mission 1 and what evidence caused the change; and (Q3) what the MVP handles poorly, why, and what to improve next. It must also disclose AI prompts/tools/decisions in an Evidence Log, provide a public GitHub repository with README and no secrets, provide an online demo if available or explain why not and give README local-run instructions, and provide a video no longer than five minutes covering problem → chosen proof → demo → hard case → limitation.

| Official criterion | Current status | Evidence / remaining proof |
|---|---|---|
| Selected MVP slice and feasibility rationale | NEEDS DEMO EVIDENCE | Implementation and Gate F/G pointers above; Q1 draft is in README. Need an evaluator-facing actual run showing why the slice proves feasibility. |
| End-to-end question → research → sources → grounded conclusion → user-verifiable evidence | NEEDS DEMO EVIDENCE | Gate F is a recorded live run; create current, readable demo artifacts for at least two distinct questions. |
| More than one research question handled | GAP — evidence | No current two-run artifact is attached to this map. |
| Important conclusions grounded in specific evidence | NEEDS DEMO EVIDENCE | Grounding/traceability implementation and tests are listed above; capture an actual output and claim trace. |
| Source reliability/provenance differentiated | NEEDS DEMO EVIDENCE | Gate G shows three documents resolving to one root; capture a reviewer-facing output. Do not present Gate G's synthetic sources as market facts. |
| Missing, conflicting or uncertain information represented | NEEDS DEMO EVIDENCE | Ambiguity, conflict, stale and source-failure evaluations exist; capture an actual current run/output. |
| Quality evaluation exists | PASS — implementation | Eight executable behavioral evaluations in `tests/evals/`, plus the broader automated suite. Current-tree execution and formatted report are pending. |
| At least five evaluation scenarios | PASS — coverage | Eight scenarios inventoried in `docs/mission2-evaluation-report.md`. |
| Good, hard/unclear and weak/failure scenarios represented | PASS — design coverage; NEEDS DEMO EVIDENCE | Case mappings are in the evaluation inventory; current actual outcomes remain pending execution. |
| Each case has Expected → Actual → Pass/Fail → Learning | GAP | Existing tests contain scenarios and assertions, not the required complete result/learning record. Fill Actual only from current execution output. |
| Q1 selected slice and feasibility | DRAFT | README Q1 draft; owner review remains. |
| Q2 Mission 1 decision change and trigger | GAP — owner input | Requires the actual Mission 1 decision and evidence that changed it. No inference made. |
| Q3 limitation, cause and next priority | GAP — actual run | Complete after current evaluations and an observed hard/failure run. |
| AI Evidence Log | PARTIAL | `docs/ai-evidence-log.md` records known tools/tasks and marks unknowns. Owner verification is pending where noted. |
| README, local setup and Codex path | PARTIAL | README quickstart and stdio command added; detailed host steps in `docs/mission2-runbook.md`. Rehearsal is pending. |
| Online demo or no-deploy reason plus local instructions | GAP — owner input | No verified online URL. README has local instructions, but deployment status/reason needs owner confirmation. |
| Public GitHub repository | GAP | Current checkout has no commits or remote. No publication has occurred. |
| No API key/password/sensitive data in public material | NEEDS DEMO EVIDENCE | Publish-oriented audit of all files is still required before any public release. |
| ≤5-minute presentation covering required flow | GAP | No final video/script artifact or duration evidence yet. |
| Submission through HR/Gamota | NOT APPLICABLE at H2 | Check during final pre-submit audit; no submission was made. |

H2 remains **GAP** until mandatory report fields, current product-run evidence and owner-dependent submission facts are resolved. The detailed case inventory is in `docs/mission2-evaluation-report.md`; AI usage is in `docs/ai-evidence-log.md`.

## Remaining verification

| Gate | Remaining evidence |
|---|---|
| H1 | This provisional mapping, grounded in task-established requirements and current repository evidence |
| H2 | Official rubric read and mapped; evaluation-result, multi-question demo and submission evidence gaps remain |
| I | Reproducible runbook in `docs/mission2-runbook.md` |
| J1–J3 | Technical preflight passed: fresh locked environment, 94/94 suite, wheel/resource check, 94/94 against installed wheel, direct MCP smoke with 15 tools and successful create/readback |
| J4–J5 | After H2, real Codex smoke against final artifact with exactly 15 tools and a successful call, then final integrity/status audit |

Do not mark H, J or the overall mission complete until every mandatory rubric item has evidence, H2 is GREEN, and the final J checks pass.
