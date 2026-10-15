from __future__ import annotations

import anyio
import importlib
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import ClientSession

from gamota_research.mcp_server import create_mcp_server
from gamota_research.service import ResearchService


FIXTURE = Path(__file__).parent / "fixtures" / "store_fixture.json"
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
    "search_store_apps",
    "get_game_details",
    "get_store_chart_snapshot",
    "get_store_chart_history",
}


def _store_components():
    try:
        provider_module = importlib.import_module(
            "gamota_research.domain.fixture_provider"
        )
        service_module = importlib.import_module(
            "gamota_research.domain.store_service"
        )
        return (
            provider_module.FixtureStoreProvider(FIXTURE),
            service_module.StoreService,
        )
    except (ModuleNotFoundError, AttributeError) as error:
        pytest.fail(f"Game/store MCP capability is missing: {error}")


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


def test_game_store_tools_run_through_mcp_and_feed_metric_guardrail(repository):
    provider, store_service_type = _store_components()
    store_service = store_service_type(repository, provider)
    server = create_mcp_server(ResearchService(repository), store_service)

    async def run():
        async with _protocol_session(server) as session:
            listed = await session.list_tools()
            assert {tool.name for tool in listed.tools} == EXPECTED_TOOLS
            assert len(listed.tools) == 15

            created = await _call(
                session,
                "create_research_run",
                {"question": "Inspect synthetic store-chart observations"},
            )
            run_id = created["run_id"]
            await _call(
                session,
                "set_research_contract",
                {
                    "run_id": run_id,
                    "decision_goal": "Verify fixture chart provenance and rank semantics",
                    "geography": ["VN"],
                    "metrics": ["store_rank"],
                    "domain_tool_budget": 5,
                },
            )

            search = await _call(
                session,
                "search_store_apps",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "query": "orbit",
                },
            )
            assert search["source_mode"] == "FIXTURE"
            assert search["games"][0]["game_id"] == "synthetic-orbit-quest"

            details = await _call(
                session,
                "get_game_details",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "game_id": "synthetic-orbit-quest",
                },
            )
            assert details["game"]["source_mode"] == "FIXTURE"
            assert details["game"]["source_url"].startswith("fixture://")

            first = await _call(
                session,
                "get_store_chart_snapshot",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "chart_type": "top_free",
                    "limit": 10,
                },
            )
            second = await _call(
                session,
                "get_store_chart_snapshot",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "chart_type": "top_free",
                    "limit": 10,
                },
            )
            assert first["snapshot"]["source_mode"] == "FIXTURE"
            assert second["snapshot"]["items"][0]["rank"] == 8

            history = await _call(
                session,
                "get_store_chart_history",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "chart_type": "top_free",
                    "game_id": "synthetic-orbit-quest",
                },
            )
            assert history["movement"]["rank_change"] == 12
            assert history["source_mode"] == "FIXTURE"

            source = await _call(
                session,
                "save_research_source",
                {
                    "run_id": run_id,
                    "url": second["snapshot"]["source_url"],
                    "title": "Synthetic Google Play top-free chart fixture",
                    "source_type": "STORE_LISTING",
                    "provenance_status": "ORIGINAL",
                    "metadata": {
                        "source_mode": "FIXTURE",
                        "generated_for_testing": True,
                    },
                },
            )
            evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source["source_id"],
                    "quote": "Synthetic test observation: Orbit Quest chart rank is 8.",
                    "locator": "snapshot " + second["snapshot"]["snapshot_id"],
                    "metric": "store_rank",
                    "value": 8,
                    "unit": "rank_position",
                    "market": "VN",
                    "source_mode": "FIXTURE",
                    "metadata": {
                        "snapshot_id": second["snapshot"]["snapshot_id"],
                        "provider": second["snapshot"]["provider"],
                    },
                },
            )
            claim = await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "Revenue increased.",
                    "claim_type": "INFERENCE",
                    "target_metric": "revenue",
                    "evidence_ids": [evidence["evidence_id"]],
                },
            )
            finalized = await _call(
                session,
                "finalize_research_run",
                {"run_id": run_id, "stop_reason": "MANUAL_FINALIZE"},
            )
            claim_result = next(
                item for item in finalized["claims"]
                if item["claim_id"] == claim["claim_id"]
            )
            assert claim_result["status"] == "INVALID"
            assert any(
                issue["code"] == "METRIC_SUPPORT_MISMATCH"
                for issue in finalized["issues"]
            )

            stored_run = await _call(
                session, "get_research_run", {"run_id": run_id}
            )
            assert stored_run["budget_status"]["domain_tool_call_count"] == 5
            assert stored_run["budget_status"]["domain_budget_exhausted"] is True

    anyio.run(run)


class _CountingFixtureProvider:
    def __init__(self, provider):
        self.provider = provider
        self.provider_name = provider.provider_name
        self.source_mode = provider.source_mode
        self.calls = 0

    def search_apps(self, **kwargs):
        self.calls += 1
        return self.provider.search_apps(**kwargs)

    def get_game_details(self, **kwargs):
        self.calls += 1
        return self.provider.get_game_details(**kwargs)

    def get_chart_snapshot(self, **kwargs):
        self.calls += 1
        return self.provider.get_chart_snapshot(**kwargs)


def test_domain_budget_rejects_before_provider_and_does_not_increment_on_rejection(
    repository,
):
    fixture_provider, store_service_type = _store_components()
    provider = _CountingFixtureProvider(fixture_provider)
    server = create_mcp_server(
        ResearchService(repository), store_service_type(repository, provider)
    )

    async def run():
        async with _protocol_session(server) as session:
            created = await _call(
                session,
                "create_research_run",
                {"question": "Enforce the game-domain tool budget"},
            )
            run_id = created["run_id"]
            await _call(
                session,
                "set_research_contract",
                {"run_id": run_id, "domain_tool_budget": 1},
            )

            first = await _call(
                session,
                "search_store_apps",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "query": "orbit",
                },
            )
            assert first["games"]
            assert provider.calls == 1

            rejected = await session.call_tool(
                "get_game_details",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "game_id": "synthetic-orbit-quest",
                },
            )
            assert rejected.is_error is True
            assert provider.calls == 1

            stored_run = await _call(
                session, "get_research_run", {"run_id": run_id}
            )
            assert stored_run["budget_status"]["domain_tool_call_count"] == 1
            assert stored_run["budget_status"]["domain_budget_exhausted"] is True

    anyio.run(run)


def test_validate_only_accepts_complete_run_at_exact_budget_limits(repository):
    fixture_provider, store_service_type = _store_components()
    server = create_mcp_server(
        ResearchService(repository), store_service_type(repository, fixture_provider)
    )

    async def run():
        async with _protocol_session(server) as session:
            run_id = (await _call(
                session,
                "create_research_run",
                {"question": "Assess a valid run at exact budget limits"},
            ))["run_id"]
            await _call(
                session,
                "set_research_contract",
                {
                    "run_id": run_id,
                    "decision_goal": "Check exact budget boundary",
                    "evidence_slots": ["market_evidence"],
                    "planned_query_budget": 6,
                    "domain_tool_budget": 1,
                    "research_round_budget": 2,
                },
            )
            await _call(
                session,
                "update_research_progress",
                {
                    "run_id": run_id,
                    "reported_search_count": 6,
                    "research_round": 2,
                },
            )
            await _call(
                session,
                "search_store_apps",
                {
                    "run_id": run_id,
                    "store": "google_play",
                    "country": "VN",
                    "query": "orbit",
                },
            )
            source = await _call(
                session,
                "save_research_source",
                {"run_id": run_id, "url": "https://source.example.test"},
            )
            evidence = await _call(
                session,
                "save_research_evidence",
                {
                    "run_id": run_id,
                    "source_id": source["source_id"],
                    "quote": "A test event occurred.",
                    "locator": "paragraph 1",
                    "metadata": {"evidence_slots": ["market_evidence"]},
                },
            )
            await _call(
                session,
                "save_research_claim",
                {
                    "run_id": run_id,
                    "text": "A test event occurred.",
                    "evidence_ids": [evidence["evidence_id"]],
                },
            )

            assessment = await _call(
                session,
                "finalize_research_run",
                {
                    "run_id": run_id,
                    "stop_reason": "COVERAGE_SUFFICIENT",
                    "validate_only": True,
                },
            )

            assert assessment["status"] == "COMPLETE"
            assert assessment["finalize_allowed"] is True
            assert assessment["budget_status"]["query_budget_exhausted"] is True
            assert assessment["budget_status"]["domain_budget_exhausted"] is True
            assert assessment["budget_status"]["round_budget_exhausted"] is True
            assert assessment["budget_status"]["within_budget"] is True

    anyio.run(run)
