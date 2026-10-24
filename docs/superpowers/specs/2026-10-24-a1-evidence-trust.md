# Mission 3 A1.1 — Evidence Trust Transparency

## Goal

Make the existing MCP/report workflow state clearly which source details are supplied by the host research agent and which details the server independently established. This improves reviewability without pretending the server verified source pages.

## Product contract

- Research sources, URLs, quotations, dates, and scopes are submitted by the connected host agent.
- The server does not fetch or independently authenticate source pages in this increment.
- Report evidence may expose an optional server-generated `source_assurance` object with `status: NOT_INDEPENDENTLY_VERIFIED`, `url_origin: HOST_SUPPLIED`, `quote_origin: HOST_SUPPLIED`, and `source_retrieved_by_server: false`.
- The UI must describe this as “Not independently verified” and explain that the source URL and quotation came from the connected research agent. It must not show a success/green verified badge.
- `ABSTAIN` and `NOT_COMPARABLE` behavior remains unchanged.
- Existing MCP arguments, database schema, report envelope, and old report compatibility remain intact. Reports without `source_assurance` retain their existing structure and render without errors.
- Caller-controlled metadata must not be elevated to server-owned source assurance. Reserved assurance keys are removed from untrusted metadata paths and generated separately by the server.
- There is no outbound HTTP retrieval or network policy toggle in this increment.

## Acceptance

1. `get_claim_trace` and newly published report evidence expose accurate, server-generated assurance.
2. Forged assurance keys in incoming or legacy metadata cannot become an authoritative field.
3. A report without the optional field is still accepted and rendered.
4. Existing A1 classification remains the same for comparable conflicts and mismatched scopes.
5. Full pytest suite and web production build pass.
