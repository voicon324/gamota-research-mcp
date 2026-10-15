from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager

import anyio
import pytest
from mcp import ClientSession

from gamota_research.db import Database
from gamota_research.enums import ClaimStatus, ConfidenceLevel, IssueSeverity, IssueStatus
from gamota_research.mcp_server import create_mcp_server
from gamota_research.repository import ResearchRepository
from gamota_research.service import ResearchService
from gamota_research.validator import Validator


def _claim_with_evidence(repository, *, target_metric, evidence_metric, relation="SUPPORTS", claim_type="INFERENCE"):
    run = repository.create_run("Check claim and evidence metric compatibility")
    source = repository.save_source(
        run_id=run.id,
        url="https://example.test/metric-report",
        title="Metric report",
        source_type="REPORT",
    )
    evidence = repository.save_evidence(
        run_id=run.id,
        source_id=source.id,
        quote="A fixture observation was recorded.",
        locator="section 1",
        metric=evidence_metric,
        value=8,
        unit="rank_position" if evidence_metric == "store_rank" else None,
        market="VN",
        source_mode="FIXTURE",
    )
    fields = {
        "run_id": run.id,
        "text": "A fixture market observation was recorded.",
        "claim_type": claim_type,
    }
    if target_metric is not None:
        fields["target_metric"] = target_metric
    claim = repository.save_claim(**fields)
    repository.link_claim_evidence(claim.id, evidence.id, relation)
    return run, claim, evidence


@pytest.mark.parametrize(
    ("target_metric", "evidence_metric"),
    [
        ("revenue", "store_rank"),
        ("revenue", "downloads"),
        ("DAU", "store_rank"),
        ("downloads", "revenue"),
    ],
)
def test_supporting_evidence_with_different_metric_blocks_claim(
    repository, target_metric, evidence_metric
):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric=target_metric,
        evidence_metric=evidence_metric,
    )

    report = Validator(repository).validate_run(run.id, finalize=False)

    checked = next(item for item in report.claims if item.id == claim.id)
    issue = next(
        item
        for item in report.issues
        if item.code == "METRIC_SUPPORT_MISMATCH"
        and item.related_claim_id == claim.id
    )
    assert issue.severity == IssueSeverity.BLOCKING
    assert checked.status == ClaimStatus.INVALID
    assert checked.confidence_level == ConfidenceLevel.INSUFFICIENT


def test_same_normalized_metric_supports_claim(repository):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric="  Revenue  ",
        evidence_metric="revenue",
    )

    report = Validator(repository).validate_run(run.id, finalize=False)

    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.status == ClaimStatus.VALID
    assert not any(
        issue.code.startswith("METRIC_SUPPORT_")
        and issue.related_claim_id == claim.id
        for issue in report.issues
    )
    assert repository.get_claim(claim.id).target_metric == "revenue"


def test_context_metric_does_not_count_as_support(repository):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric="revenue",
        evidence_metric="revenue",
    )
    context_source = repository.save_source(
        run_id=run.id,
        url="https://example.test/rank-context",
        title="Rank context",
        source_type="REPORT",
    )
    context_evidence = repository.save_evidence(
        run_id=run.id,
        source_id=context_source.id,
        quote="A rank observation provides context.",
        locator="section 2",
        metric="store_rank",
        source_mode="FIXTURE",
    )
    repository.link_claim_evidence(claim.id, context_evidence.id, "CONTEXT")

    report = Validator(repository).validate_run(run.id, finalize=False)

    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.status == ClaimStatus.VALID
    assert not any(
        issue.code == "METRIC_SUPPORT_MISMATCH"
        and issue.related_claim_id == claim.id
        for issue in report.issues
    )


def test_every_metric_bearing_support_must_match_target_metric(repository):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric="revenue",
        evidence_metric="revenue",
    )
    second_source = repository.save_source(
        run_id=run.id,
        url="https://example.test/rank-support",
        title="Rank support",
        source_type="REPORT",
    )
    second_evidence = repository.save_evidence(
        run_id=run.id,
        source_id=second_source.id,
        quote="A store rank observation was recorded.",
        locator="section 3",
        metric="store_rank",
        source_mode="FIXTURE",
    )
    repository.link_claim_evidence(claim.id, second_evidence.id, "SUPPORTS")

    report = Validator(repository).validate_run(run.id, finalize=False)

    issue = next(
        item
        for item in report.issues
        if item.code == "METRIC_SUPPORT_MISMATCH"
        and item.related_claim_id == claim.id
    )
    assert issue.evidence_id == second_evidence.id
    assert next(item for item in report.claims if item.id == claim.id).status == ClaimStatus.INVALID


def test_supporting_evidence_without_metric_is_explicitly_blocked(repository):
    run, claim, evidence = _claim_with_evidence(
        repository,
        target_metric="revenue",
        evidence_metric=None,
    )

    report = Validator(repository).validate_run(run.id, finalize=False)

    checked = next(item for item in report.claims if item.id == claim.id)
    issue = next(
        item
        for item in report.issues
        if item.code == "METRIC_SUPPORT_UNKNOWN"
        and item.related_claim_id == claim.id
    )
    assert issue.severity == IssueSeverity.BLOCKING
    assert issue.evidence_id == evidence.id
    assert checked.status == ClaimStatus.INVALID


@pytest.mark.parametrize("claim_type", ["FACT", "INFERENCE"])
def test_metric_support_requires_declared_claim_metric(repository, claim_type):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric=None,
        evidence_metric="revenue",
        claim_type=claim_type,
    )

    report = Validator(repository).validate_run(run.id, finalize=False)

    checked = next(item for item in report.claims if item.id == claim.id)
    issue = next(
        item
        for item in report.issues
        if item.code == "CLAIM_METRIC_UNSPECIFIED"
        and item.related_claim_id == claim.id
    )
    assert issue.severity == IssueSeverity.BLOCKING
    assert checked.status == ClaimStatus.INVALID


def test_qualitative_claim_with_metricless_support_remains_valid(repository):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric=None,
        evidence_metric=None,
    )

    report = Validator(repository).validate_run(run.id, finalize=False)

    checked = next(item for item in report.claims if item.id == claim.id)
    assert checked.status == ClaimStatus.VALID
    assert not any(
        issue.code in {
            "METRIC_SUPPORT_UNKNOWN",
            "METRIC_SUPPORT_MISMATCH",
            "CLAIM_METRIC_UNSPECIFIED",
        }
        and issue.related_claim_id == claim.id
        for issue in report.issues
    )


def test_metric_issue_persists_and_resolves_after_claim_metric_is_fixed(repository):
    run, claim, _ = _claim_with_evidence(
        repository,
        target_metric="revenue",
        evidence_metric="store_rank",
    )
    validator = Validator(repository)

    first = validator.validate_run(run.id, finalize=False)
    issue = next(
        item
        for item in repository.list_issues(run.id)
        if item.code == "METRIC_SUPPORT_MISMATCH"
    )
    assert issue.status == IssueStatus.OPEN

    repository.save_claim(
        id=claim.id,
        run_id=claim.run_id,
        text=claim.text,
        claim_type=claim.claim_type,
        target_metric="store_rank",
    )
    second = validator.validate_run(run.id, finalize=False)

    assert any(item.id == issue.id and item.status == IssueStatus.RESOLVED for item in second.issues)
    assert next(item for item in second.claims if item.id == claim.id).status == ClaimStatus.VALID


def test_existing_claims_table_gets_nullable_target_metric_migration(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    raw = sqlite3.connect(path)
    raw.executescript(
        """
        CREATE TABLE research_runs (
            id TEXT PRIMARY KEY, question TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, finalized_at TEXT, stop_reason TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE claims (
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES research_runs(id),
            text TEXT NOT NULL, claim_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING', confidence_level TEXT NOT NULL,
            confidence_rationale TEXT, metadata_json TEXT NOT NULL DEFAULT '{}'
        );
        INSERT INTO research_runs(id, question, status, created_at)
            VALUES ('legacy-run', 'legacy question', 'CREATED', '2025-01-01');
        INSERT INTO claims(id, run_id, text, claim_type, confidence_level)
            VALUES ('legacy-claim', 'legacy-run', 'legacy fact', 'FACT', 'UNASSESSED');
        """
    )
    raw.commit()
    raw.close()

    database = Database(path)
    try:
        claim = ResearchRepository(database).get_claim("legacy-claim")
        with database.connection() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(claims)")}
        assert "target_metric" in columns
        assert claim.target_metric is None
    finally:
        database.close()


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


def test_mcp_save_claim_exposes_and_persists_target_metric(repository):
    server = create_mcp_server(ResearchService(repository))

    async def run():
        async with _protocol_session(server) as session:
            tools = await session.list_tools()
            save_claim = next(tool for tool in tools.tools if tool.name == "save_research_claim")
            assert "target_metric" in save_claim.input_schema["properties"]
            created = await session.call_tool(
                "create_research_run", {"question": "Persist target metric over MCP"}
            )
            run_id = created.structured_content["run_id"]
            source_result = await session.call_tool(
                "save_research_source",
                {"run_id": run_id, "url": "https://example.test", "source_type": "REPORT"},
            )
            evidence_result = await session.call_tool(
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source_result.structured_content["source_id"],
                    "quote": "Revenue evidence",
                    "locator": "section 1",
                    "metric": "revenue",
                },
            )
            saved = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "Revenue was measured.",
                    "evidence_ids": [evidence_result.structured_content["evidence_id"]],
                    "target_metric": " revenue ",
                },
            )
            assert saved.is_error is False
            claim = repository.get_claim(saved.structured_content["claim_id"])
            assert claim.target_metric == "revenue"

    anyio.run(run)
