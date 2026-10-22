from __future__ import annotations

import json

import pytest

from gamota_research.reports import ReportService, validate_game_decision_brief
from gamota_research.service import ResearchService
from gamota_research.validator import Validator


def _publish_directional_pair(repository, output_dir, *, second_metric="revenue_growth"):
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
            period_end="2025-06-30",
            observed_at="2025-06-30",
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
        {"question": run.question, "metrics": ["revenue_growth"]},
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
