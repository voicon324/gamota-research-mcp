from __future__ import annotations

import anyio
from contextlib import asynccontextmanager
from mcp import ClientSession

from gamota_research.mcp_server import create_mcp_server
from gamota_research.service import ResearchService


EXPECTED_TOOLS = {
    "create_research_run",
    "set_research_contract",
    "update_research_progress",
    "save_research_source",
    "save_research_evidence",
    "save_research_claim",
    "record_research_issue",
    "finalize_research_run",
    "get_research_run",
    "get_claim_trace",
    "get_claim_lineage_audit",
}


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


async def _call(session, name: str, arguments: dict):
    result = await session.call_tool(name, arguments)
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


def test_mcp_protocol_exposes_research_lifecycle_and_preserves_core_behavior(
    repository,
):
    server = create_mcp_server(ResearchService(repository))

    async def run():
        async with _protocol_session(server) as session:
            tool_list = await session.list_tools()
            assert {tool.name for tool in tool_list.tools} == EXPECTED_TOOLS
            update_progress = next(
                tool
                for tool in tool_list.tools
                if tool.name == "update_research_progress"
            )
            assert "reported_search_count" in update_progress.input_schema[
                "properties"
            ]
            assert "research_round" in update_progress.input_schema["properties"]
            assert "domain_tool_call_count" not in update_progress.input_schema[
                "properties"
            ]
            finalize_tool = next(
                tool
                for tool in tool_list.tools
                if tool.name == "finalize_research_run"
            )
            assert "stop_reason" not in finalize_tool.input_schema.get(
                "required", []
            )
            assert "validate_only" in finalize_tool.input_schema["properties"]
            tool_names = {tool.name for tool in tool_list.tools}
            assert "web_search" not in tool_names
            assert not any("game" in name or "store" in name for name in tool_names)

            run_result = await _call(
                session,
                "create_research_run",
                {"question": "Track a hypothetical mobile-game signal"},
            )
            run_id = run_result["run_id"]
            assert run_result["status"] == "CREATED"

            contract_result = await _call(
                session,
                "set_research_contract",
                {
                    "run_id": run_id,
                    "decision_goal": "Record a traceable research result",
                    "geography": ["VN"],
                    "time_scope": {"kind": "recent"},
                    "metrics": ["qualitative_signal"],
                    "segments": ["mobile games"],
                    "assumptions": ["This is a test fixture"],
                    "evidence_slots": ["market_evidence"],
                    "planned_query_budget": 10,
                    "domain_tool_budget": 10,
                    "research_round_budget": 2,
                },
            )
            assert contract_result["contract"]["assumptions"] == [
                "This is a test fixture"
            ]

            progress_result = await _call(
                session,
                "update_research_progress",
                {
                    "run_id": run_id,
                    "reported_search_count": 4,
                    "research_round": 1,
                },
            )
            assert progress_result["reported_search_count"] == 4
            assert progress_result["research_round"] == 1
            assert progress_result["budget_status"]["within_budget"] is True

            issue_result = await _call(
                session,
                "record_research_issue",
                {
                    "run_id": run_id,
                    "issue_type": "SOURCE_FAILURE",
                    "severity": "INFO",
                    "description": "An optional test source was unavailable.",
                },
            )

            source_result = await _call(
                session,
                "save_research_source",
                {
                    "run_id": run_id,
                    "url": "https://example.test/fictional-market-report",
                    "title": "Hypothetical market report",
                    "publisher": "Example Research",
                    "source_type": "REPORT",
                    "provenance_status": "ORIGINAL",
                },
            )
            evidence_result = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source_result["source_id"],
                    "quote": "A hypothetical qualitative signal is described.",
                    "locator": "section 1",
                    "source_mode": "FIXTURE",
                    "metadata": {"evidence_slots": ["market_evidence"]},
                },
            )
            missing_evidence = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "A claim cannot be saved without evidence.",
                    "evidence_ids": [],
                },
            )
            assert missing_evidence.is_error is True
            invalid_evidence = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "A claim cannot link to a missing evidence record.",
                    "evidence_ids": ["missing-evidence"],
                },
            )
            assert invalid_evidence.is_error is True
            claim_result = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "The hypothetical report describes a qualitative signal.",
                    "claim_type": "INFERENCE",
                    "evidence_ids": [evidence_result["evidence_id"]],
                },
            )
            claim_id = claim_result["claim_id"]

            missing_stop_reason = await session.call_tool(
                "finalize_research_run", {"run_id": run_id}
            )
            assert missing_stop_reason.is_error is True
            unchanged_run = await _call(
                session, "get_research_run", {"run_id": run_id}
            )
            assert unchanged_run["research_run"]["status"] == "CREATED"
            assert unchanged_run["research_run"]["stop_reason"] is None
            assert unchanged_run["research_run"]["finalized_at"] is None

            finalize_result = await _call(
                session,
                "finalize_research_run",
                {"run_id": run_id, "stop_reason": "COVERAGE_SUFFICIENT"},
            )
            assert finalize_result["status"] == "COMPLETE"
            assert finalize_result["stop_reason"] == "COVERAGE_SUFFICIENT"
            assert finalize_result["claims"][0]["status"] == "VALID"

            read_result = await _call(
                session, "get_research_run", {"run_id": run_id}
            )
            assert read_result["research_run"]["id"] == run_id
            assert read_result["research_contract"]["decision_goal"] == (
                "Record a traceable research result"
            )
            assert any(
                issue["id"] == issue_result["issue_id"]
                for issue in read_result["issues"]
            )

            trace = await _call(
                session, "get_claim_trace", {"claim_id": claim_id}
            )
            assert trace["claim"]["id"] == claim_id
            assert trace["evidence"][0]["evidence"]["id"] == evidence_result[
                "evidence_id"
            ]
            assert trace["evidence"][0]["source"]["url"].endswith(
                "fictional-market-report"
            )

            audit = await _call(
                session, "get_claim_lineage_audit", {"claim_id": claim_id}
            )
            assert audit["independent_root_count"] == 1
            assert audit["supporting_independent_root_count"] == 1

            error = await session.call_tool(
                "get_claim_trace", {"claim_id": "missing-claim"}
            )
            assert error.is_error is True

    anyio.run(run)


def test_mcp_can_link_evidence_to_an_existing_claim_without_creating_a_duplicate(
    repository,
):
    server = create_mcp_server(ResearchService(repository))

    async def run():
        async with _protocol_session(server) as session:
            run_id = (await _call(
                session, "create_research_run", {"question": "Existing claim linking"}
            ))["run_id"]
            source_a = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://a.example.test", "provenance_status": "ORIGINAL"},
            )
            evidence_a = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source_a["source_id"],
                    "quote": "The event opened on 15 September 2026.",
                    "locator": "paragraph 1",
                    "metric": "open_beta_start_date",
                    "value": "2026-09-15",
                    "market": "Vietnam",
                    "source_mode": "LIVE",
                },
            )
            claim_text = "The event opened in Vietnam on 15 September 2026."
            claim_a = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": claim_text,
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [evidence_a["evidence_id"]],
                },
            )
            claim_id = claim_a["claim_id"]

            source_b = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://b.example.test", "provenance_status": "ORIGINAL"},
            )
            evidence_b = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source_b["source_id"],
                    "quote": "The event opened on 15 September 2026.",
                    "locator": "paragraph 2",
                    "metric": "open_beta_start_date",
                    "value": "2026-09-15",
                    "market": "Vietnam",
                    "source_mode": "LIVE",
                },
            )

            linked = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim_id,
                    "text": claim_text,
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [evidence_b["evidence_id"]],
                    "relation": "SUPPORTS",
                },
            )
            assert linked == {
                "claim_id": claim_id,
                "linked_evidence_ids": [evidence_b["evidence_id"]],
            }
            assert len(repository.list_claims(run_id)) == 1
            trace = await _call(session, "get_claim_trace", {"claim_id": claim_id})
            assert {item["evidence"]["id"] for item in trace["evidence"]} == {
                evidence_a["evidence_id"],
                evidence_b["evidence_id"],
            }
            audit = await _call(
                session, "get_claim_lineage_audit", {"claim_id": claim_id}
            )
            assert audit["independent_root_count"] == 2

            overwrite = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim_id,
                    "text": "A different claim must not overwrite this one.",
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [evidence_b["evidence_id"]],
                },
            )
            assert overwrite.is_error is True
            assert repository.get_claim(claim_id).text == claim_text

            duplicate = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim_id,
                    "text": claim_text,
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [evidence_b["evidence_id"]],
                    "relation": "SUPPORTS",
                },
            )
            assert duplicate["claim_id"] == claim_id
            assert len(repository.list_claims(run_id)) == 1
            trace = await _call(session, "get_claim_trace", {"claim_id": claim_id})
            assert len(trace["evidence"]) == 2

            other_run = (await _call(
                session,
                "create_research_run",
                {"question": "Cross-run claim linking must fail"},
            ))["run_id"]
            other_source = await _call(
                session,
                "save_research_source",
                {"run_id": other_run, "url": "https://other.example.test"},
            )
            other_evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": other_run,
                    "source_id": other_source["source_id"],
                    "quote": "The event opened on 15 September 2026.",
                    "locator": "paragraph 1",
                },
            )
            cross_run = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": other_run,
                    "existing_claim_id": claim_id,
                    "text": claim_text,
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [other_evidence["evidence_id"]],
                },
            )
            assert cross_run.is_error is True

    anyio.run(run)


def test_mcp_can_backfill_null_metric_on_existing_claim_without_relinking(repository):
    service = ResearchService(repository)
    server = create_mcp_server(service)

    async def run():
        async with _protocol_session(server) as session:
            run_id = (await _call(
                session, "create_research_run", {"question": "Repair claim metric"}
            ))["run_id"]
            source = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://repair.example.test", "provenance_status": "ORIGINAL"},
            )
            evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source["source_id"],
                    "quote": "The event opened on 15 September 2026.",
                    "locator": "paragraph 1",
                    "metric": "open_beta_start_date",
                    "value": "2026-09-15",
                    "market": "Vietnam",
                    "source_mode": "LIVE",
                },
            )
            second_source = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://repair-second.example.test"},
            )
            second_evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": second_source["source_id"],
                    "quote": "The event opened on 15 September 2026.",
                    "locator": "paragraph 2",
                    "metric": "open_beta_start_date",
                    "value": "2026-09-15",
                    "market": "Vietnam",
                    "source_mode": "LIVE",
                },
            )
            claim = service.save_claim(
                run_id=run_id,
                text="The event opened in Vietnam on 15 September 2026.",
                claim_type="FACT",
                target_metric=None,
                status="VALIDATED",
                confidence_level="HIGH",
                confidence_rationale="preserve this rationale",
                metadata={"legacy": True},
            )
            missing_evidence = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim.id,
                    "text": claim.text,
                    "claim_type": "FACT",
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [],
                },
            )
            assert missing_evidence.is_error is True
            assert repository.get_claim(claim.id).target_metric is None
            service.link_claim_evidence(claim.id, evidence["evidence_id"], "SUPPORTS")
            service.link_claim_evidence(claim.id, second_evidence["evidence_id"], "SUPPORTS")

            non_metric_source = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://no-metric.example.test"},
            )
            non_metric_evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": non_metric_source["source_id"],
                    "quote": "The announcement discusses the event.",
                    "locator": "paragraph 1",
                },
            )
            claim_without_metric = service.save_claim(
                run_id=run_id,
                text="A separate claim with no metric-bearing evidence.",
                target_metric=None,
            )
            service.link_claim_evidence(
                claim_without_metric.id, non_metric_evidence["evidence_id"], "CONTEXT"
            )
            no_metric = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim_without_metric.id,
                    "text": claim_without_metric.text,
                    "claim_type": "FACT",
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [],
                },
            )
            assert no_metric.is_error is True
            assert repository.get_claim(claim_without_metric.id).target_metric is None

            mismatch = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim.id,
                    "text": claim.text,
                    "claim_type": "FACT",
                    "target_metric": "release_date",
                    "evidence_ids": [],
                },
            )
            assert mismatch.is_error is True
            assert repository.get_claim(claim.id).target_metric is None

            conflicting_source = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://conflicting-metric.example.test"},
            )
            conflicting_evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": conflicting_source["source_id"],
                    "quote": "A different metric is described.",
                    "locator": "paragraph 1",
                    "metric": "release_date",
                    "value": "2026-09-15",
                    "market": "Vietnam",
                },
            )
            mixed_metrics_claim = service.save_claim(
                run_id=run_id,
                text="Claim with conflicting linked metric types.",
                target_metric=None,
            )
            service.link_claim_evidence(mixed_metrics_claim.id, evidence["evidence_id"], "SUPPORTS")
            service.link_claim_evidence(
                mixed_metrics_claim.id, conflicting_evidence["evidence_id"], "SUPPORTS"
            )
            mixed_metrics = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": mixed_metrics_claim.id,
                    "text": mixed_metrics_claim.text,
                    "claim_type": "FACT",
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [],
                },
            )
            assert mixed_metrics.is_error is True
            assert repository.get_claim(mixed_metrics_claim.id).target_metric is None

            repaired = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim.id,
                    "text": claim.text,
                    "claim_type": "FACT",
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [],
                    "relation": "SUPPORTS",
                },
            )

            assert repaired == {"claim_id": claim.id, "linked_evidence_ids": []}
            repaired_claim = repository.get_claim(claim.id)
            assert repaired_claim.target_metric == "open_beta_start_date"
            assert repaired_claim.text == claim.text
            assert repaired_claim.claim_type == claim.claim_type
            assert repaired_claim.status == claim.status
            assert repaired_claim.confidence_level == claim.confidence_level
            assert repaired_claim.confidence_rationale == claim.confidence_rationale
            assert repaired_claim.metadata == claim.metadata
            assert len(repository.list_claims(run_id)) == 3
            empty_noop = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim.id,
                    "text": claim.text,
                    "claim_type": "FACT",
                    "target_metric": "open_beta_start_date",
                    "evidence_ids": [],
                },
            )
            assert empty_noop.is_error is False
            different_metric = await session.call_tool(
                "save_research_claim",
                {
                    "run_id": run_id,
                    "existing_claim_id": claim.id,
                    "text": claim.text,
                    "claim_type": "FACT",
                    "target_metric": "release_date",
                    "evidence_ids": [],
                },
            )
            assert different_metric.is_error is True
            trace = await _call(session, "get_claim_trace", {"claim_id": claim.id})
            assert len(trace["evidence"]) == 2

    anyio.run(run)


def test_mcp_validate_only_returns_finalization_assessment_without_writes(repository):
    server = create_mcp_server(ResearchService(repository))

    async def run():
        async with _protocol_session(server) as session:
            run_id = (await _call(
                session, "create_research_run", {"question": "Pure assessment"}
            ))["run_id"]
            await _call(
                session,
                "set_research_contract",
                {
                    "run_id": run_id,
                    "decision_goal": "Assess without finalizing",
                    "evidence_slots": ["release_signal", "independent_crosscheck"],
                    "planned_query_budget": 6,
                    "domain_tool_budget": 20,
                    "research_round_budget": 2,
                },
            )
            source = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://source.example.test", "provenance_status": "ORIGINAL"},
            )
            evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source["source_id"],
                    "quote": "A test event occurred.",
                    "locator": "paragraph 1",
                    "metadata": {"evidence_slots": ["release_signal"]},
                    "source_mode": "LIVE",
                },
            )
            claim = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "A test event occurred.",
                    "evidence_ids": [evidence["evidence_id"]],
                },
            )

            before_run = repository.get_run(run_id)
            before_claims = repository.list_claims(run_id)
            before_issues = repository.list_issues(run_id)
            before_budget = repository.get_research_budget_status(run_id)
            assessment = await _call(
                session,
                "finalize_research_run",
                {
                    "run_id": run_id,
                    "validate_only": True,
                },
            )

            assert assessment["finalize_allowed"] is False
            assert assessment["claims"][0]["claim_id"] == claim["claim_id"]
            assert assessment["claims"][0]["status"] == "VALID"
            assert assessment["missing_evidence_slots"] == ["independent_crosscheck"]
            after_run = repository.get_run(run_id)
            assert after_run == before_run
            assert repository.list_claims(run_id) == before_claims
            assert repository.list_issues(run_id) == before_issues
            assert repository.get_research_budget_status(run_id) == before_budget

    anyio.run(run)
