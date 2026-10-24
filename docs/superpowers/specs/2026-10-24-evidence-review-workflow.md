# Evidence Review Workflow

## Intent

Make published game-market reports usable for a reviewer who needs to judge source quality signals, freshness, evidence coverage, conflicts, and what research should happen next. Codex/Claude remain responsible for web discovery with their native tools; the MCP records the audit trail and the site explains it.

## Goals

- Show each source's declared type and provenance (`ORIGINAL`, `DERIVED`, `UNKNOWN`) without presenting these host-supplied values as independently verified or converting them into a fabricated trust score.
- Show the source publication date, metric observation date, and explicit freshness cutoff together. Label freshness as current, stale, unknown, or not assessed based only on those dates.
- Put the evidence quote, locator, claim validation/confidence, source link, and MCP verification boundary together for every finding and conflict.
- Offer a context-preserving follow-up prompt for every open issue, including weak/unknown provenance, stale/unknown freshness, missing evidence, invalid claims, and conflicts.
- Tell connected agents the required workflow: search with native tools, prefer direct sources, compare scope and dates, preserve uncertainty, validate, publish, read back, and summarize in chat.
- Preserve report schema 1.0 and old report compatibility with optional fields.

## Non-goals

- Do not fetch arbitrary source URLs from the MCP server, claim quotes were verified, or assign numeric source-trust scores.
- Do not perform generic web search or automatically continue research without the host agent.
- Do not implement all five alternative Change Requests; the assigned request remains A1.
- Do not auto-select a market winner when comparable evidence conflicts.

## Approaches

1. Add a date/provenance review view using already stored facts (chosen). It is auditable, fast, and avoids server-side network retrieval.
2. Add server-side source fetching. Deferred because this introduces SSRF/egress, parsing, and citation verification risks beyond the current request and requires a separately reviewed retrieval boundary.
3. Add a numeric source-quality score. Rejected because stored metadata cannot support a defensible score and would imply certainty the system does not have.

## Design

The report projection includes optional `source_type` and `scope.freshness_cutoff`. Markdown and web views render a consistent evidence-review block for every source/evidence pair. Freshness derives from both publication and observation dates; without a cutoff it is `NOT_ASSESSED`, a missing date is `UNKNOWN`, an earlier date is `STALE`, otherwise `CURRENT`. Provenance remains a declared field; `UNKNOWN` and `DERIVED` become review prompts, not claims that a source is false. Every actionable issue can produce a follow-up prompt that carries the original question, scope, issue, existing evidence, and exact URLs. MCP server instructions state the full research loop and require natural-language results in the same chat with the exact report link returned by the MCP.

## Constraints

- Keep schema `1.0` and make new fields optional.
- Never fetch host-supplied URLs server-side.
- Never label host-supplied quotes as independently verified.
- Preserve existing published artifacts and report identifiers.
- Test first; verify full Python suite, frontend production build, and live deployment before claiming completion.
