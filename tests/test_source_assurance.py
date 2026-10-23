from __future__ import annotations

import json


def test_claim_trace_marks_host_supplied_source_without_trusting_metadata(
    database, repository
):
    run = repository.create_run("Check evidence provenance")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/source",
        title="Fixture source",
        metadata={
            "publisher_note": "Keep this metadata",
            "source_assurance": {"status": "VERIFIED"},
        },
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="The source reports 12% growth.",
        locator="Summary",
        metadata={
            "research_note": "Keep this metadata",
            "source_assurance": {"status": "VERIFIED"},
            "source_verification": {"quote_status": "MATCHED"},
        },
    )
    claim = repository.save_claim(run_id=run.id, text="Growth was reported.")
    repository.link_claim_evidence(claim.id, evidence.id, "SUPPORTS")

    # Simulate old rows written before the server reserved assurance metadata.
    with database.transaction() as connection:
        source_metadata = json.dumps({"source_assurance": {"status": "VERIFIED"}})
        evidence_metadata = json.dumps(
            {"source_verification": {"quote_status": "MATCHED"}}
        )
        connection.execute(
            "UPDATE sources SET metadata_json = ? WHERE id = ?",
            (source_metadata, source.id),
        )
        connection.execute(
            "UPDATE evidence SET metadata_json = ? WHERE id = ?",
            (evidence_metadata, evidence.id),
        )

    trace = repository.get_claim_trace(claim.id)
    linked = trace["evidence"][0]

    assert linked["source_assurance"] == {
        "status": "NOT_INDEPENDENTLY_VERIFIED",
        "url_origin": "HOST_SUPPLIED",
        "quote_origin": "HOST_SUPPLIED",
        "source_retrieved_by_server": False,
        "message": (
            "The connected research agent supplied the source URL and quotation; "
            "the MCP server did not independently retrieve the source."
        ),
    }
    assert linked["evidence"]["metadata"] == {}
    assert linked["source"]["metadata"] == {}


def test_assurance_metadata_filter_preserves_unrelated_keys(repository):
    run = repository.create_run("Preserve evidence notes")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/source",
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="Fixture quote.",
        locator="Body",
        metadata={
            "review_note": "Needs a human check",
            "Source_Assurance": {"status": "VERIFIED"},
            "source_verification": {"quote_status": "MATCHED"},
        },
    )

    stored = repository.get_evidence(evidence.id)

    assert stored is not None
    assert stored.metadata == {"review_note": "Needs a human check"}
