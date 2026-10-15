from __future__ import annotations

import json
from contextlib import asynccontextmanager

import anyio
import pytest
from mcp import ClientSession

from gamota_research.mcp_server import create_mcp_server
from gamota_research.reports import ReportService, validate_game_decision_brief
from gamota_research.service import ResearchService
from gamota_research.validator import Validator


@asynccontextmanager
async def _protocol_session(server):
    client_to_server_send, server_receive = anyio.create_memory_object_stream(0)
    server_to_client_send, client_receive = anyio.create_memory_object_stream(0)
    async with anyio.create_task_group() as task_group:
        task_group.start_soon(
            server._lowlevel_server.run,
            server_receive,
            server_to_client_send,
            server._lowlevel_server.create_initialization_options(),
        )
        try:
            async with ClientSession(client_receive, client_to_server_send) as session:
                await session.initialize()
                yield session
        finally:
            task_group.cancel_scope.cancel()


def _completed_run(repository) -> tuple[str, str]:
    service = ResearchService(repository)
    run = service.create_run("Does the competitor show durable traction?")
    service.set_research_contract(
        run.id,
        {
            "question": run.question,
            "decision_goal": "Decide whether to prioritize a deeper teardown",
            "geography": ["Global"],
            "metrics": ["downloads"],
        },
    )
    source = service.save_source(
        run_id=run.id,
        url="https://example.com/official-news",
        title="Official milestone",
        publisher="Publisher",
    )
    evidence = service.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="The game surpassed 100 million downloads.",
        locator="paragraph 2",
        metric="downloads",
        value=100,
        unit="million",
        market="Global",
    )
    claim = service.save_claim(
        run_id=run.id,
        text="The publisher reported more than 100 million global downloads.",
        target_metric="downloads",
        metadata={"report_type": "finding"},
    )
    service.link_claim_evidence(claim.id, evidence.id)
    estimate = service.save_claim(
        run_id=run.id,
        text="An estimate indicates approximately 100 million global downloads.",
        claim_type="ESTIMATE",
        target_metric="downloads",
    )
    service.link_claim_evidence(estimate.id, evidence.id)
    recommendation = service.save_claim(
        run_id=run.id,
        text="Prioritize a deeper product teardown before committing to feature replication.",
        claim_type="RECOMMENDATION",
    )
    service.link_claim_evidence(recommendation.id, evidence.id)
    service.set_stop_reason(run.id, "COVERAGE_SUFFICIENT")
    Validator(repository).validate_run(run.id, finalize=True)
    return run.id, claim.id


def test_publish_creates_valid_json_markdown_and_manifest(repository, tmp_path):
    run_id, _ = _completed_run(repository)
    reports = ReportService(repository, tmp_path)

    report = reports.publish_game_decision_brief(
        run_id=run_id,
        title="Competitor traction brief",
        game="Example Game",
        verdict="Public evidence confirms the milestone, but not retention or revenue.",
        platforms=["iOS", "Android"],
    )

    assert validate_game_decision_brief(report) == []
    assert report["schema_version"] == "1.0"
    assert report["scope"]["question"] == "Does the competitor show durable traction?"
    assert report["findings"][0]["evidence_ids"]
    assert next(item for item in report["findings"] if item["type"] == "estimate")
    signal = next(item for item in report["metrics"] if item["metric"] == "downloads")
    assert signal["value"] == 100
    assert signal["unit"] == "million"
    assert signal["data_type"] == "estimate"
    assert len(signal["evidence_ids"]) == 1
    assert report["recommendations"][0]["text"].startswith("Prioritize a deeper")
    assert report["sources"][0]["url"] == "https://example.com/official-news"
    report_path = tmp_path / report["report"]["id"] / "report.json"
    markdown_path = tmp_path / report["report"]["id"] / "report.md"
    manifest_path = tmp_path / "index.json"
    assert json.loads(report_path.read_text()) == report
    assert "Competitor traction brief" in markdown_path.read_text()
    assert json.loads(manifest_path.read_text())["reports"][0]["id"] == report["report"]["id"]
    assert reports.get_report(report["report"]["id"]) == report


def test_report_validation_finds_orphan_evidence_and_missing_decision(repository):
    errors = validate_game_decision_brief(
        {
            "schema_version": "1.0",
            "report": {"id": "r1", "type": "game_decision_brief"},
            "scope": {"question": "A question"},
            "summary": {},
            "findings": [
                {
                    "id": "f1",
                    "statement": "A finding",
                    "type": "fact",
                    "confidence": "medium",
                    "evidence_ids": ["missing-evidence"],
                },
                {
                    "id": "f2",
                    "statement": "A causal interpretation",
                    "type": "inference",
                    "confidence": "high",
                    "evidence_ids": ["missing-evidence"],
                },
            ],
            "recommendations": [],
            "unknowns": [],
            "sources": [],
            "evidence": [],
        }
    )

    assert any("summary.verdict" in error for error in errors)
    assert any("missing-evidence" in error for error in errors)
    assert any("inference confidence cannot be high" in error for error in errors)


def test_cannot_publish_unfinalized_run(repository, tmp_path):
    service = ResearchService(repository)
    run = service.create_run("Question")
    reports = ReportService(repository, tmp_path)

    with pytest.raises(ValueError, match="finalized"):
        reports.publish_game_decision_brief(
            run_id=run.id,
            title="Brief",
            game="Example",
            verdict="Unknown",
        )


def test_report_publish_list_and_get_are_available_through_mcp(repository, tmp_path):
    run_id, _ = _completed_run(repository)
    report_service = ReportService(repository, tmp_path)
    server = create_mcp_server(
        ResearchService(repository), report_service=report_service
    )

    async def run():
        async with _protocol_session(server) as session:
            tools = {tool.name for tool in (await session.list_tools()).tools}
            assert {
                "publish_game_decision_brief",
                "list_published_reports",
                "get_published_report",
            } <= tools
            published = await session.call_tool(
                "publish_game_decision_brief",
                {
                    "run_id": run_id,
                    "title": "MCP lifecycle brief",
                    "game": "Example Game",
                    "verdict": "Milestone verified within the stated scope.",
                },
            )
            assert not published.is_error, published.content
            report_id = published.structured_content["report_id"]
            listed = await session.call_tool("list_published_reports", {})
            assert not listed.is_error
            assert listed.structured_content["reports"][0]["id"] == report_id
            loaded = await session.call_tool(
                "get_published_report", {"report_id": report_id}
            )
            assert not loaded.is_error
            assert loaded.structured_content["report"]["id"] == report_id

    anyio.run(run)
