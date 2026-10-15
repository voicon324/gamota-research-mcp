# R2 — Wuthering Waves mobile revenue scope conflict

**Scenario result:** PASS — hard/conflicting/uncertain case.
**Mode:** real web research using native Codex search and Gamota MCP evidence storage; no store or fixture acquisition calls.
**Run:** `d5bf9f0f-a484-43d6-9385-4a9f65aec47e` · **Implementation:** `63922f41e398f7e1ad040878669dc48dded41581`
**Repository outcome:** finalized **PARTIAL / WEAK**, stop reason `BUDGET_EXHAUSTED`.

## Question and bounded conclusion

Can public evidence substantiate at least US$100 million in worldwide iOS App Store plus Google Play mobile revenue during Wuthering Waves’ first 30 launch days? The verified launch date is May 22, 2024; the contract defines the window as May 22 through June 20 inclusive, with launch day counted as day one.

**Finding: not substantiated.** None of the four reviewed source pages reports mobile-only revenue for that exact contract window. June calendar-month estimates, an early combined PC-and-mobile estimate, and a later cumulative mobile milestone measure different periods or scopes. They cannot be combined to claim the first-30-day threshold.

## Evidence and source quality

- [PocketGamer.biz launch and revenue report](https://www.pocketgamer.biz/wuthering-waves-sails-past-100-million-in-under-two-months/) reports the May 22 launch, a later AppMagic mobile gross milestone above $100 million, App Store + Google Play coverage, and estimate exclusions. It is specialist trade press relaying AppMagic, not audited publisher data.
- [GameDev Reports’ June 2024 AppMagic digest](https://gamedevreports.substack.com/p/appmagic-top-mobile-games-by-revenue-66e) reports a June net mobile estimate of $41.9 million. This is a calendar-month estimate.
- [Game World Observer’s June 17 report](https://gameworldobserver.com/2024/06/17/wuthering-waves-110-million-revenue-pc-and-mobile) relays GameLook’s cumulative estimate above $110.2 million across PC and mobile. That is not mobile-only.
- A second AppMagic-related estimate in PocketGamer.biz reports June gross mobile revenue of $59.9 million and separately distinguishes net from gross.

The June net and gross figures are separate estimates and definitions; neither directly measures the contract window. The later $100 million mobile gross milestone cannot be backdated. The PC-plus-mobile figure cannot satisfy a mobile-only test. AppMagic estimates exclude non-mobile platforms, third-party Android stores, web shops and advertising revenue; they are not comprehensive publisher revenue.

## Repository validator and safe stopping

All seven atomic factual claims are **VALID** and every claim target metric matches its linked evidence metric. The run covers **6 of 7** required evidence slots. The sole missing slot is `first_month_mobile_only_revenue_estimate`, because no directly sourced estimate was found for the exact worldwide iOS + Google Play window.

The persisted `MISSING_EVIDENCE` issue is **WARNING / OPEN**. The validator also emits a **BLOCKING / OPEN major GAP** for the uncovered required slot. This is expected repository behavior, covered by `tests/test_stop_conditions.py::test_missing_required_evidence_slot_creates_blocking_gap_and_partial`; it causes the final **PARTIAL / WEAK** status. The blocking GAP is the safe-stop result, not a claim-grounding error. There are no numeric-grounding or metric-support mismatch issues.

## Run and validation

- Native web searches: 5 (within budget); pages read: 4.
- Sources: 4; evidence records: 10; factual claims: 7, all VALID.
- Domain/store calls: 0; contract domain-tool budget is 1 because the schema requires a positive integer.
- Required slots: 7; covered: 6; missing: 1.
- Final status: PARTIAL / WEAK; stop reason: `BUDGET_EXHAUSTED`.

See [`research_run.json`](research_run.json) for the exact run, contract, coverage, budget, validation and tool-call records. See [`trace.json`](trace.json) for post-finalization claim-to-evidence-to-source traces.
