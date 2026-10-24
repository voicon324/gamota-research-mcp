from __future__ import annotations

import json

import pytest

from gamota_research.reports import ReportService, validate_game_decision_brief
from gamota_research.service import ResearchService
from gamota_research.validator import Validator


def _publish_directional_pair(
    repository,
    output_dir,
    *,
    second_metric="revenue_growth",
    freshness_cutoff=None,
    source_published_at="2025-05-15",
    observation_date="2025-06-30",
    provenance_status="UNKNOWN",
):
    service = ResearchService(repository)
    run = service.create_run("Does the game show revenue growth in Vietnam?")
    service.set_research_contract(
        run.id,
        {
            "question": run.question,
            "decision_goal": "Assess market direction",
            "geography": ["VN"],
            "metrics": ["revenue_growth"],
            "time_scope": {"start": "2025-01-01", "end": "2025-06-30"},
            **({"freshness_cutoff": freshness_cutoff} if freshness_cutoff else {}),
        },
    )
    evidence_ids = []
    for index, (metric, direction) in enumerate(
        [("revenue_growth", "UP"), (second_metric, "DOWN")], start=1
    ):
        source = service.save_source(
            run_id=run.id,
            url=f"https://example.test/source-{index}",
            title=f"Fixture source {index}",
            publisher=f"Publisher {index}",
            source_type="REPORT",
            published_at=source_published_at,
            provenance_status=provenance_status,
        )
        evidence = service.save_evidence(
            run_id=run.id,
            source_id=source.id,
            quote=f"Reported {direction.lower()} {metric.replace('_', ' ')}.",
            locator="Results, table 1",
            metric=metric,
            value=8 if direction == "UP" else -3,
            unit="%",
            market="VN",
            period_start="2025-01-01",
            period_end=observation_date,
            observed_at=observation_date,
            source_mode="FIXTURE",
            metadata={"direction": direction},
        )
        evidence_ids.append(evidence.id)
    claim = service.save_claim(
        run_id=run.id,
        text="The available sources indicate a directional revenue trend.",
        claim_type="INFERENCE",
        target_metric="revenue_growth",
    )
    for evidence_id in evidence_ids:
        service.link_claim_evidence(claim.id, evidence_id, "SUPPORTS")
    service.set_stop_reason(run.id, "COVERAGE_SUFFICIENT")
    Validator(repository).validate_run(run.id, finalize=True)
    report = ReportService(repository, output_dir).publish_game_decision_brief(
        run_id=run.id,
        title="Revenue direction review",
        game="Fixture Game",
        verdict="The evidence is insufficient to select a reliable market direction.",
        markets=["VN"],
        platforms=["iOS", "Android"],
    )
    return report


def test_comparable_opposite_sources_publish_abstention_with_evidence(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)

    issue = next(item for item in report["unknowns"] if item["type"] == "CONFLICT")
    assert issue["resolution"] == "ABSTAIN"
    assert issue["comparability"] == "COMPARABLE"
    assert set(issue["evidence_ids"]) == {item["id"] for item in report["evidence"]}
    assert set(issue["directions"].values()) == {"UP", "DOWN"}
    assert issue["comparison_signature"]
    assert report["summary"]["directional_decision"]["outcome"] == "ABSTAIN"
    assert report["summary"]["confidence"] == "low"
    markdown = (tmp_path / report["report"]["id"] / "report.md").read_text()
    assert "ABSTAIN" in markdown
    assert "Fixture source 1" in markdown and "Fixture source 2" in markdown
    assert "does not establish" in markdown
    assert markdown.index("## System assessment") < markdown.index(
        "## Publishing agent assessment (unverified)"
    )


def test_scope_mismatch_is_not_falsely_published_as_conflict(repository, tmp_path):
    report = _publish_directional_pair(
        repository, tmp_path, second_metric="downloads_growth"
    )

    issue = next(
        item for item in report["unknowns"] if item["type"] == "NOT_COMPARABLE"
    )
    assert issue["resolution"] == "NOT_COMPARABLE"
    assert issue["comparability"] == "NOT_COMPARABLE"
    assert "metric_mismatch" in issue["reasons"]
    assert not any(item["type"] == "CONFLICT" for item in report["unknowns"])
    assert report["summary"]["directional_decision"]["outcome"] == "NOT_COMPARABLE"


def test_published_evidence_exposes_server_assurance(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)

    for item in report["evidence"]:
        assert item["source_assurance"] == {
            "status": "NOT_INDEPENDENTLY_VERIFIED",
            "url_origin": "HOST_SUPPLIED",
            "quote_origin": "HOST_SUPPLIED",
            "source_retrieved_by_server": False,
            "message": (
                "The connected research agent supplied the source URL and quotation; "
                "the MCP server did not independently retrieve the source."
            ),
        }


def test_report_exposes_source_review_facts_for_each_evidence(repository, tmp_path):
    report = _publish_directional_pair(
        repository, tmp_path, freshness_cutoff="2025-01-01"
    )

    assert report["scope"]["freshness_cutoff"] == "2025-01-01"
    assert all(source["source_type"] == "REPORT" for source in report["sources"])
    for item in report["evidence"]:
        assert item["observed_at"] == "2025-06-30"
        assert item["review"] == {
            "freshness_status": "CURRENT",
            "freshness_cutoff": "2025-01-01",
            "publication_date": "2025-05-15",
            "observation_date": "2025-06-30",
            "provenance_status": "UNKNOWN",
            "source_type": "REPORT",
            "verification_status": "NOT_INDEPENDENTLY_VERIFIED",
            "review_reasons": ["Source provenance is unknown."],
            "next_steps": [
                "Open the source link and confirm the saved quotation at its locator.",
                "Compare the source's metric, market, platform, period, and method with the claim.",
                "Trace this citation to an original publisher or dataset and record its source lineage.",
            ],
        }

    markdown = (tmp_path / report["report"]["id"] / "report.md").read_text()
    assert "## Evidence review" in markdown
    assert "freshness: CURRENT" in markdown
    assert "cutoff 2025-01-01" in markdown
    assert "provenance: UNKNOWN" in markdown
    assert "not independently verified" in markdown
    assert "Next: Trace this citation to an original publisher" in markdown


def test_report_marks_missing_publication_date_as_unknown_freshness(repository, tmp_path):
    report = _publish_directional_pair(
        repository,
        tmp_path,
        freshness_cutoff="2025-01-01",
        source_published_at=None,
        provenance_status="DERIVED",
    )
    review = report["evidence"][0]["review"]

    assert review["freshness_status"] == "UNKNOWN"
    assert review["publication_date"] is None
    assert review["observation_date"] == "2025-06-30"
    assert review["provenance_status"] == "DERIVED"
    assert "Source publication date is unknown." in review["review_reasons"]
    assert "Evidence is derived from another source." in review["review_reasons"]
    assert any("original document or dataset" in step for step in review["next_steps"])


def test_report_marks_old_publication_as_stale_even_with_recent_observation(repository, tmp_path):
    report = _publish_directional_pair(
        repository,
        tmp_path,
        freshness_cutoff="2025-01-01",
        source_published_at="2023-01-01",
        observation_date="2025-06-30",
    )

    assert report["evidence"][0]["review"]["freshness_status"] == "STALE"
    assert any(
        "newer publication" in step
        for step in report["evidence"][0]["review"]["next_steps"]
    )


def test_report_requires_both_dates_to_assess_freshness(repository, tmp_path):
    report = _publish_directional_pair(
        repository,
        tmp_path,
        freshness_cutoff="2025-01-01",
        observation_date=None,
    )

    review = report["evidence"][0]["review"]
    assert review["freshness_status"] == "UNKNOWN"
    assert review["publication_date"] == "2025-05-15"
    assert review["observation_date"] is None
    assert "Metric observation date is unknown." in review["review_reasons"]


def test_report_without_freshness_cutoff_does_not_claim_current_data(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)

    assert report["evidence"][0]["review"]["freshness_status"] == "NOT_ASSESSED"


def test_report_issues_include_targeted_next_research_steps(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)
    issue = next(item for item in report["unknowns"] if item["type"] == "CONFLICT")

    assert issue["next_steps"] == [
        "Search for additional sources that measure the same metric, market, platform, period, and population.",
        "Compare methods and dates; keep the result unresolved when evidence remains conflicting or out of scope.",
    ]


def test_publish_remains_compatible_with_trace_without_assurance(repository, tmp_path):
    original_get_trace = repository.get_claim_trace

    def legacy_trace(claim_id):
        trace = original_get_trace(claim_id)
        if trace:
            for link in trace["evidence"]:
                link.pop("source_assurance", None)
        return trace

    repository.get_claim_trace = legacy_trace
    report = _publish_directional_pair(repository, tmp_path)

    assert report["evidence"]
    assert all("source_assurance" not in item for item in report["evidence"])


def test_report_validation_rejects_unknown_conflict_evidence_id(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)
    conflict = next(item for item in report["unknowns"] if item["type"] == "CONFLICT")
    conflict["evidence_ids"].append("missing-evidence")
    conflict["directions"]["missing-evidence"] = "UP"

    errors = validate_game_decision_brief(report)

    assert any("unknowns[" in error and "missing-evidence" in error for error in errors)


def test_report_validation_rejects_broken_directional_issue_references(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)
    report["summary"]["directional_decision"]["issue_ids"] = ["missing-issue"]

    errors = validate_game_decision_brief(report)

    assert any("directional_decision.issue_ids" in error for error in errors)


def test_report_validation_handles_malformed_direction_metadata(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)
    conflict = next(item for item in report["unknowns"] if item["type"] == "CONFLICT")
    conflict["directions"][conflict["evidence_ids"][0]] = {"unexpected": "object"}
    conflict["resolution"] = ["ABSTAIN"]

    errors = validate_game_decision_brief(report)

    assert any("directions." in error and "must be UP or DOWN" in error for error in errors)
    assert any("resolution is not supported" in error for error in errors)


def test_report_validation_rejects_malformed_directional_outcome(repository, tmp_path):
    report = _publish_directional_pair(repository, tmp_path)
    report["summary"]["directional_decision"]["outcome"] = {"value": "ABSTAIN"}

    errors = validate_game_decision_brief(report)

    assert any("directional_decision.outcome is not supported" in error for error in errors)


def test_legacy_v1_report_without_a1_fields_remains_valid():
    report = {
        "schema_version": "1.0",
        "report": {
            "id": "legacy-report", "type": "game_decision_brief", "title": "Old",
            "game": "Game", "as_of": "2025-01-01", "status": "published",
            "research_run_id": "run-1",
        },
        "scope": {"question": "A question"},
        "summary": {"verdict": "A bounded result", "confidence": "medium"},
        "findings": [], "recommendations": [], "unknowns": [], "sources": [],
        "evidence": [],
    }

    assert validate_game_decision_brief(report) == []


def test_supported_report_keeps_existing_trace_and_has_no_directional_decision(repository, tmp_path):
    service = ResearchService(repository)
    run = service.create_run("Was the launch milestone reported?")
    service.set_research_contract(
        run.id,
        {"question": run.question, "metrics": ["downloads"]},
    )
    source = service.save_source(
        run_id=run.id,
        url="https://example.test/milestone",
        title="Official milestone",
        publisher="Publisher",
    )
    evidence = service.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="The game passed 10 million downloads.",
        locator="paragraph 2",
        metric="downloads",
        value=10,
        unit="million",
        market="Global",
    )
    claim = service.save_claim(
        run_id=run.id,
        text="The publisher reported 10 million downloads.",
        target_metric="downloads",
    )
    service.link_claim_evidence(claim.id, evidence.id)
    service.set_stop_reason(run.id, "COVERAGE_SUFFICIENT")
    Validator(repository).validate_run(run.id, finalize=True)

    report = ReportService(repository, tmp_path).publish_game_decision_brief(
        run_id=run.id,
        title="Supported milestone",
        game="Fixture Game",
        verdict="The publisher reported the milestone.",
    )

    assert report["schema_version"] == "1.0"
    assert "directional_decision" not in report["summary"]
    assert report["findings"][0]["evidence_ids"] == [evidence.id]
    assert report["sources"][0]["url"] == "https://example.test/milestone"
    assert ReportService(repository, tmp_path).get_report(report["report"]["id"]) == report


def test_missing_evidence_does_not_create_a_directional_decision(repository, tmp_path):
    service = ResearchService(repository)
    run = service.create_run("Is there enough evidence for the market trend?")
    service.set_research_contract(
        run.id,
        {
            "question": run.question,
            "metrics": ["revenue_growth"],
            "evidence_slots": ["mobile revenue in the first 30 days"],
        },
    )
    claim = service.save_claim(
        run_id=run.id,
        text="The market is growing.",
        target_metric="revenue_growth",
    )
    service.set_stop_reason(run.id, "INSUFFICIENT_DATA")
    Validator(repository).validate_run(run.id, finalize=True)

    report = ReportService(repository, tmp_path).publish_game_decision_brief(
        run_id=run.id,
        title="Evidence gap",
        game="Fixture Game",
        verdict="No directional conclusion is supported.",
    )

    assert "directional_decision" not in report["summary"]
    assert not any(item["id"] == claim.id for item in report["findings"])
    issue = next(item for item in report["unknowns"] if item["id"] == f"claim-{claim.id}")
    assert issue["type"] == "INVALID_CLAIM"
    assert any(item["type"] == "MISSING_EVIDENCE_SLOT" for item in report["unknowns"])
    markdown = (tmp_path / report["report"]["id"] / "report.md").read_text()
    assert markdown.index("## Evidence gaps") < markdown.index("## Findings")
    assert "The market is growing." in markdown
    assert markdown.index("## System assessment") < markdown.index(
        "## Publishing agent assessment (unverified)"
    )
