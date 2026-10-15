from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .enums import ClaimType, EvidenceRelation, IssueSeverity, IssueType, ProvenanceStatus
from .enums import SourceMode, SourceType, StopReason
from .domain.store_service import StoreService
from .service import ResearchService
from .reports import ReportService
from .validator import Validator


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    return value


def _require_run(service: ResearchService, run_id: str):
    run = service.get_run(run_id)
    if run is None:
        raise ToolError(f"Research run not found: {run_id}")
    return run


def register_research_tools(
    server: MCPServer,
    service: ResearchService,
    validator: Validator,
    store_service: StoreService | None = None,
    report_service: ReportService | None = None,
) -> None:
    """Register MCP adapters for the existing research service and validator."""

    @server.tool(description="Create an empty research run. The host provides its own plan and web search.")
    def create_research_run(question: str) -> dict[str, Any]:
        try:
            run = service.create_run(question)
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {
            "run_id": run.id,
            "question": run.question,
            "status": _json_value(run.status),
            "created_at": run.created_at,
        }

    @server.tool(description="Persist the host-authored scope and research contract for an existing run.")
    def set_research_contract(
        run_id: str,
        decision_goal: str | None = None,
        geography: list[str] | None = None,
        time_scope: str | dict[str, Any] | None = None,
        metrics: list[str] | None = None,
        segments: list[str] | None = None,
        assumptions: list[str] | None = None,
        evidence_slots: list[str] | None = None,
        freshness_cutoff: str | None = None,
        planned_query_budget: int | None = None,
        domain_tool_budget: int | None = None,
        research_round_budget: int | None = None,
    ) -> dict[str, Any]:
        run = _require_run(service, run_id)
        contract: dict[str, Any] = {"question": run.question}
        optional_fields = {
            "decision_goal": decision_goal,
            "geography": geography,
            "time_scope": time_scope,
            "metrics": metrics,
            "segments": segments,
            "assumptions": assumptions,
            "evidence_slots": evidence_slots,
            "freshness_cutoff": freshness_cutoff,
            "planned_query_budget": planned_query_budget,
            "domain_tool_budget": domain_tool_budget,
            "research_round_budget": research_round_budget,
        }
        contract.update(
            {name: value for name, value in optional_fields.items() if value is not None}
        )
        try:
            stored = service.set_research_contract(run_id, contract)
            budget = service.get_research_budget_status(run_id)
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {"run_id": run_id, "contract": stored, "budget_status": budget}

    @server.tool(description="Record host-reported native searches and the current research round.")
    def update_research_progress(
        run_id: str,
        reported_search_count: int | None = None,
        research_round: int | None = None,
    ) -> dict[str, Any]:
        _require_run(service, run_id)
        try:
            progress = service.update_research_progress(
                run_id,
                reported_search_count=reported_search_count,
                research_round=research_round,
            )
            budget = service.get_research_budget_status(run_id)
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {"run_id": run_id, **progress, "budget_status": budget}

    @server.tool(description="Save source metadata supplied by the host; this tool does not fetch the URL.")
    def save_research_source(
        run_id: str,
        url: str,
        title: str | None = None,
        publisher: str | None = None,
        published_at: str | None = None,
        accessed_at: str | None = None,
        source_type: SourceType = SourceType.WEB,
        parent_source_id: str | None = None,
        root_source_id: str | None = None,
        provenance_status: ProvenanceStatus = ProvenanceStatus.UNKNOWN,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _require_run(service, run_id)
        fields: dict[str, Any] = {
            "run_id": run_id,
            "url": url,
            "title": title,
            "publisher": publisher,
            "published_at": published_at,
            "source_type": source_type,
            "parent_source_id": parent_source_id,
            "root_source_id": root_source_id,
            "provenance_status": provenance_status,
            "metadata": metadata or {},
        }
        if accessed_at is not None:
            fields["accessed_at"] = accessed_at
        try:
            source = service.save_source(**fields)
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {"source_id": source.id, "root_source_id": source.root_source_id}

    @server.tool(description="Save an atomic evidence record for a source already stored in this run.")
    def save_research_evidence(
        run_id: str,
        source_id: str,
        quote: str,
        locator: str,
        observed_at: str | None = None,
        metric: str | None = None,
        value: str | int | float | None = None,
        unit: str | None = None,
        market: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        scope: str | None = None,
        method: str | None = None,
        source_mode: SourceMode = SourceMode.LIVE,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _require_run(service, run_id)
        try:
            evidence = service.save_evidence(
                run_id=run_id,
                source_id=source_id,
                quote=quote,
                locator=locator,
                observed_at=observed_at,
                metric=metric,
                value=value,
                unit=unit,
                market=market,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                method=method,
                source_mode=source_mode,
                metadata=metadata or {},
            )
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {"evidence_id": evidence.id, "root_source_id": evidence.root_source_id}

    @server.tool(description="Save a claim and link its evidence IDs before validation.")
    def save_research_claim(
        run_id: str,
        text: str,
        evidence_ids: list[str],
        claim_type: ClaimType = ClaimType.FACT,
        target_metric: str | None = None,
        relation: EvidenceRelation = EvidenceRelation.SUPPORTS,
        metadata: dict[str, Any] | None = None,
        existing_claim_id: str | None = None,
    ) -> dict[str, Any]:
        _require_run(service, run_id)
        unique_evidence_ids = list(dict.fromkeys(evidence_ids))
        if not unique_evidence_ids and existing_claim_id is None:
            raise ToolError("evidence_ids must contain at least one saved evidence ID")
        for evidence_id in unique_evidence_ids:
            evidence = service.repository.get_evidence(evidence_id)
            if evidence is None:
                raise ToolError(f"Evidence not found: {evidence_id}")
            if evidence.run_id != run_id:
                raise ToolError("Claim and evidence must belong to the same research run")
        try:
            if existing_claim_id is not None:
                claim = service.repository.get_claim(existing_claim_id)
                if claim is None:
                    raise ToolError(f"Claim not found: {existing_claim_id}")
                if claim.run_id != run_id:
                    raise ToolError("Claim and evidence must belong to the same research run")
                metric_repair = (
                    claim.target_metric is None
                    and target_metric is not None
                    and not unique_evidence_ids
                )
                if (
                    claim.text != text
                    or claim.claim_type != claim_type
                    or (claim.target_metric != target_metric and not metric_repair)
                ):
                    raise ToolError(
                        "Existing claim text, claim_type, and target_metric must match; "
                        "existing claim fields are not updated"
                    )
                if metric_repair:
                    if metadata is not None and metadata != claim.metadata:
                        raise ToolError("Existing claim metadata must match during metric repair")
                    service.repository.backfill_claim_target_metric(claim.id, target_metric)
            else:
                claim = service.save_claim(
                    run_id=run_id,
                    text=text,
                    claim_type=claim_type,
                    target_metric=target_metric,
                    metadata=metadata or {},
                )
            for evidence_id in unique_evidence_ids:
                service.link_claim_evidence(claim.id, evidence_id, relation)
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {"claim_id": claim.id, "linked_evidence_ids": unique_evidence_ids}

    @server.tool(description="Record a host-observed research issue such as ambiguity or a failed source.")
    def record_research_issue(
        run_id: str,
        issue_type: IssueType,
        severity: IssueSeverity,
        description: str,
        related_claim_id: str | None = None,
        related_evidence_id: str | None = None,
        related_source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _require_run(service, run_id)
        try:
            issue = service.save_issue(
                run_id=run_id,
                code=issue_type.value,
                message=description,
                severity=severity,
                related_claim_id=related_claim_id,
                evidence_id=related_evidence_id,
                source_id=related_source_id,
                metadata=metadata or {},
            )
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        return {"issue_id": issue.id}

    @server.tool(description="Finalize a run with an explicit reason and the deterministic validator.")
    def finalize_research_run(
        run_id: str,
        stop_reason: StopReason | None = None,
        validate_only: bool = False,
    ) -> dict[str, Any]:
        _require_run(service, run_id)
        try:
            if validate_only:
                report = validator.validate_run(
                    run_id,
                    finalize=True,
                    persist=False,
                    stop_reason_override=stop_reason,
                )
                coverage = service.get_research_evidence_slot_coverage(run_id)
                budget = service.get_research_budget_status(run_id)
                blocking_issues = [
                    issue
                    for issue in report.issues
                    if _json_value(issue.severity) in {"BLOCKING", "ERROR"}
                    and _json_value(issue.status) == "OPEN"
                ]
                finalize_allowed = (
                    _json_value(report.status) == "COMPLETE"
                    and not coverage["missing"]
                    and budget["within_budget"]
                    and not blocking_issues
                    and all(
                        _json_value(claim.status) == "VALID"
                        for claim in report.claims
                    )
                )
            else:
                if stop_reason is None:
                    raise ValueError(
                        "An explicit stop_reason is required to finalize a research run"
                    )
                service.set_stop_reason(run_id, stop_reason)
                report = validator.validate_run(run_id, finalize=True)
        except (TypeError, ValueError, KeyError) as error:
            raise ToolError(str(error)) from error
        result = {
            "run_id": report.run_id,
            "status": report.status,
            "confidence": report.confidence,
            "stop_reason": report.stop_reason,
            "claims": [
                {
                    "claim_id": claim.id,
                    "status": claim.status,
                    "confidence_level": claim.confidence_level,
                    "confidence_rationale": claim.confidence_rationale,
                }
                for claim in report.claims
            ],
            "issues": report.issues,
        }
        if validate_only:
            result.update(
                {
                    "validate_only": True,
                    "finalize_allowed": finalize_allowed,
                    "evidence_slot_coverage": coverage,
                    "missing_evidence_slots": coverage["missing"],
                    "budget_status": budget,
                }
            )
        return _json_value(result)

    @server.tool(description="Read a run, its contract, current budget, claims and issues.")
    def get_research_run(run_id: str) -> dict[str, Any]:
        run = _require_run(service, run_id)
        contract = service.get_research_contract(run_id)
        budget = service.get_research_budget_status(run_id) if contract else None
        coverage = service.get_research_evidence_slot_coverage(run_id) if contract else None
        return {
            "research_run": _json_value(run),
            "research_contract": contract,
            "budget_status": budget,
            "evidence_slot_coverage": coverage,
            "claims": _json_value(service.repository.list_claims(run_id)),
            "issues": _json_value(service.repository.list_issues(run_id)),
        }

    @server.tool(description="Return a claim and its evidence quotes, locators and source URLs.")
    def get_claim_trace(claim_id: str) -> dict[str, Any]:
        trace = service.trace_claim(claim_id)
        if trace is None:
            raise ToolError(f"Claim not found: {claim_id}")
        return trace

    @server.tool(description="Return document counts, independent roots, and evidence-source lineage for a claim.")
    def get_claim_lineage_audit(claim_id: str) -> dict[str, Any]:
        audit = service.get_claim_lineage_audit(claim_id)
        if audit is None:
            raise ToolError(f"Claim not found: {claim_id}")
        return audit

    if report_service is not None:

        @server.tool(
            description=(
                "Publish an immutable Game Decision Brief from a finalized research run. "
                "The verdict is host-authored; findings and recommendations are built "
                "only from validated, evidence-linked claims. The report is written to "
                "the configured public reports directory for the website to read."
            )
        )
        def publish_game_decision_brief(
            run_id: str,
            title: str,
            game: str,
            verdict: str,
            platforms: list[str] | None = None,
            markets: list[str] | None = None,
        ) -> dict[str, Any]:
            try:
                report = report_service.publish_game_decision_brief(
                    run_id=run_id,
                    title=title,
                    game=game,
                    verdict=verdict,
                    platforms=platforms,
                    markets=markets,
                )
            except (TypeError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error
            return {
                "report_id": report["report"]["id"],
                "report_path": f"{report['report']['id']}/report.json",
                "markdown_path": f"{report['report']['id']}/report.md",
                "published": True,
                "research_status": report["report"]["research_status"],
                "finding_count": len(report["findings"]),
                "recommendation_count": len(report["recommendations"]),
                "unknown_count": len(report["unknowns"]),
                "evidence_count": len(report["evidence"]),
            }

        @server.tool(description="List published Game Decision Brief metadata for the report library.")
        def list_published_reports() -> dict[str, Any]:
            try:
                return report_service.list_reports()
            except (OSError, ValueError) as error:
                raise ToolError(f"Could not read published report manifest: {error}") from error

        @server.tool(description="Read a published report, including findings, sources, and evidence excerpts.")
        def get_published_report(report_id: str) -> dict[str, Any]:
            try:
                return report_service.get_report(report_id)
            except (OSError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error

    if store_service is not None:

        def _consume_domain_call(run_id: str) -> None:
            _require_run(service, run_id)
            try:
                service.consume_domain_tool_budget(run_id)
            except (TypeError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error

        @server.tool(
            description=(
                "Search the configured store provider. Apple RSS searches the Vietnam "
                "Top Free and Top Paid app feeds; results are not a games-only catalog."
            )
        )
        def search_store_apps(
            run_id: str, store: str, country: str, query: str
        ) -> dict[str, Any]:
            _consume_domain_call(run_id)
            try:
                games = store_service.search_apps(
                    store=store, country=country, query=query
                )
            except (TypeError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error
            return {
                "run_id": run_id,
                "games": _json_value(games),
                "provider": store_service.provider_name,
                "source_mode": _json_value(store_service.source_mode),
            }

        @server.tool(
            description=(
                "Read app metadata from the configured store provider. With Apple RSS, "
                "an app is discoverable only while present in its supported top-app feeds."
            )
        )
        def get_game_details(
            run_id: str, store: str, country: str, game_id: str
        ) -> dict[str, Any]:
            _consume_domain_call(run_id)
            try:
                game = store_service.get_game_details(
                    store=store, country=country, game_id=game_id
                )
            except (TypeError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error
            return {
                "run_id": run_id,
                "game": _json_value(game),
                "provider": store_service.provider_name,
                "source_mode": _json_value(store_service.source_mode),
            }

        @server.tool(
            description=(
                "Observe and persist a store chart snapshot. Apple RSS supports only "
                "Vietnam Top Free Apps and Top Paid Apps, not games-only or Top Grossing."
            )
        )
        def get_store_chart_snapshot(
            run_id: str,
            store: str,
            country: str,
            chart_type: str,
            limit: int | None = 20,
        ) -> dict[str, Any]:
            _consume_domain_call(run_id)
            try:
                snapshot = store_service.get_chart_snapshot(
                    run_id=run_id,
                    store=store,
                    country=country,
                    chart_type=chart_type,
                    limit=limit,
                )
            except (TypeError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error
            return {"run_id": run_id, "snapshot": _json_value(snapshot)}

        @server.tool(
            description=(
                "Read persisted store-rank history and deterministic rank movement. "
                "Rank is a visibility proxy, not revenue, downloads, or DAU."
            )
        )
        def get_store_chart_history(
            run_id: str,
            store: str,
            country: str,
            chart_type: str,
            game_id: str,
            start: str | None = None,
            end: str | None = None,
        ) -> dict[str, Any]:
            _consume_domain_call(run_id)
            try:
                history = store_service.get_chart_history(
                    run_id=run_id,
                    store=store,
                    country=country,
                    chart_type=chart_type,
                    game_id=game_id,
                    start=start,
                    end=end,
                )
            except (TypeError, ValueError, KeyError) as error:
                raise ToolError(str(error)) from error
            return _json_value(history)
