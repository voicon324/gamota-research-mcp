from __future__ import annotations

import json
from dataclasses import replace
from enum import Enum
from typing import Any, TypeVar

from .contract import ResearchContract
from .comparability import normalize_metric
from .db import Database
from .domain.models import StoreChartSnapshot
from .enums import (
    ClaimStatus,
    ClaimType,
    ConfidenceLevel,
    EvidenceRelation,
    IssueSeverity,
    IssueStatus,
    ProvenanceStatus,
    RunStatus,
    SourceMode,
    SourceType,
)
from .models import Claim, ClaimEvidence, Evidence, ResearchIssue, ResearchRun, Source
from .provenance import build_claim_lineage_audit
from .source_assurance import (
    sanitize_untrusted_metadata,
    source_assurance_for_host_supplied_source,
)

E = TypeVar("E", bound=Enum)


def _value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _enum(enum_type: type[E], value: str) -> E | str:
    try:
        return enum_type(value)
    except ValueError:
        return value


def _metadata_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _metadata(value: str) -> dict[str, Any]:
    return json.loads(value or "{}")


class ResearchRepository:
    """Persistence operations for the six research-core entities."""

    def __init__(self, database: Database):
        self.database = database

    def create_run(self, question: str) -> ResearchRun:
        run = ResearchRun(question=question)
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO research_runs
                   (id, question, status, created_at, finalized_at, stop_reason, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.id,
                    run.question,
                    _value(run.status),
                    run.created_at,
                    run.finalized_at,
                    run.stop_reason,
                    _metadata_json(run.metadata),
                ),
            )
        return run

    def get_run(self, run_id: str) -> ResearchRun | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
        if row is None:
            return None
        return ResearchRun(
            id=row["id"],
            question=row["question"],
            status=_enum(RunStatus, row["status"]),
            created_at=row["created_at"],
            finalized_at=row["finalized_at"],
            stop_reason=row["stop_reason"],
            metadata=_metadata(row["metadata_json"]),
        )

    def update_run_validation(
        self,
        run_id: str,
        status: RunStatus | str,
        finalized_at: str | None,
        stop_reason: str | None,
    ) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE research_runs
                   SET status = ?, finalized_at = ?, stop_reason = ?
                   WHERE id = ?""",
                (_value(status), finalized_at, stop_reason, run_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Research run not found: {run_id}")

    def set_research_contract(
        self, run_id: str, contract: ResearchContract | dict[str, Any]
    ) -> dict[str, Any]:
        normalized = ResearchContract.from_value(contract).to_dict()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT metadata_json FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Research run not found: {run_id}")
            metadata = _metadata(row["metadata_json"])
            metadata["research_contract"] = normalized
            metadata.setdefault(
                "research_progress",
                {
                    "reported_search_count": 0,
                    "domain_tool_call_count": 0,
                    "research_round": 0,
                },
            )
            connection.execute(
                "UPDATE research_runs SET metadata_json = ? WHERE id = ?",
                (_metadata_json(metadata), run_id),
            )
        return normalized

    def get_research_contract(self, run_id: str) -> dict[str, Any] | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        value = run.metadata.get("research_contract")
        if value is None:
            return None
        return ResearchContract.from_value(value).to_dict()

    def get_research_progress(self, run_id: str) -> dict[str, int]:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(f"Research run not found: {run_id}")
        progress = run.metadata.get("research_progress") or {}
        return {
            "reported_search_count": int(progress.get("reported_search_count", 0)),
            "domain_tool_call_count": int(progress.get("domain_tool_call_count", 0)),
            "research_round": int(progress.get("research_round", 0)),
        }

    def update_research_progress(
        self,
        run_id: str,
        *,
        reported_search_count: int | None = None,
        domain_tool_call_count: int | None = None,
        research_round: int | None = None,
    ) -> dict[str, int]:
        updates = {
            "reported_search_count": reported_search_count,
            "domain_tool_call_count": domain_tool_call_count,
            "research_round": research_round,
        }
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT metadata_json FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Research run not found: {run_id}")
            metadata = _metadata(row["metadata_json"])
            if "research_contract" not in metadata:
                raise ValueError("Set a research contract before updating progress")
            progress = {
                "reported_search_count": 0,
                "domain_tool_call_count": 0,
                "research_round": 0,
                **(metadata.get("research_progress") or {}),
            }
            for name, value in updates.items():
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"{name} must be a non-negative integer")
                if value < progress[name]:
                    raise ValueError(f"{name} cannot decrease")
                progress[name] = value
            metadata["research_progress"] = progress
            connection.execute(
                "UPDATE research_runs SET metadata_json = ? WHERE id = ?",
                (_metadata_json(metadata), run_id),
            )
        return progress

    def consume_domain_tool_budget(self, run_id: str) -> dict[str, int]:
        """Atomically reserve one domain-tool call before provider work begins."""
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT metadata_json FROM research_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Research run not found: {run_id}")
            metadata = _metadata(row["metadata_json"])
            contract_value = metadata.get("research_contract")
            if contract_value is None:
                raise ValueError("Set a research contract before using domain tools")
            contract = ResearchContract.from_value(contract_value).to_dict()
            progress = {
                "reported_search_count": 0,
                "domain_tool_call_count": 0,
                "research_round": 0,
                **(metadata.get("research_progress") or {}),
            }
            if progress["domain_tool_call_count"] >= contract["domain_tool_budget"]:
                raise ValueError("Domain tool budget exhausted for research run")
            progress["domain_tool_call_count"] += 1
            metadata["research_progress"] = progress
            connection.execute(
                "UPDATE research_runs SET metadata_json = ? WHERE id = ?",
                (_metadata_json(metadata), run_id),
            )
        return progress

    def get_research_budget_status(self, run_id: str) -> dict[str, Any]:
        contract = self.get_research_contract(run_id)
        if contract is None:
            if self.get_run(run_id) is None:
                raise KeyError(f"Research run not found: {run_id}")
            raise ValueError("Set a research contract before checking its budget")
        progress = self.get_research_progress(run_id)
        query_exhausted = (
            progress["reported_search_count"] >= contract["planned_query_budget"]
        )
        domain_exhausted = (
            progress["domain_tool_call_count"] >= contract["domain_tool_budget"]
        )
        round_exhausted = (
            progress["research_round"] >= contract["research_round_budget"]
        )
        return {
            **progress,
            "planned_query_budget": contract["planned_query_budget"],
            "domain_tool_budget": contract["domain_tool_budget"],
            "research_round_budget": contract["research_round_budget"],
            "query_budget_exhausted": query_exhausted,
            "domain_budget_exhausted": domain_exhausted,
            "round_budget_exhausted": round_exhausted,
            # Exhaustion means no additional work can be started from this
            # counter. Reaching a configured limit is still valid; it becomes
            # a budget violation only when a counter exceeds that limit.
            "within_budget": (
                progress["reported_search_count"]
                <= contract["planned_query_budget"]
                and progress["domain_tool_call_count"]
                <= contract["domain_tool_budget"]
                and progress["research_round"]
                <= contract["research_round_budget"]
            ),
        }

    def set_run_stop_reason(self, run_id: str, stop_reason: str) -> None:
        if not isinstance(stop_reason, str) or not stop_reason.strip():
            raise ValueError("stop_reason must be a non-empty string")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE research_runs SET stop_reason = ? WHERE id = ?",
                (stop_reason.strip(), run_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Research run not found: {run_id}")

    def get_research_evidence_slot_coverage(self, run_id: str) -> dict[str, Any]:
        contract = self.get_research_contract(run_id)
        if contract is None:
            if self.get_run(run_id) is None:
                raise KeyError(f"Research run not found: {run_id}")
            raise ValueError("Set a research contract before checking evidence slots")
        with self.database.connection() as connection:
            evidence_rows = connection.execute(
                "SELECT metadata_json FROM evidence WHERE run_id = ?", (run_id,)
            ).fetchall()
            claim_rows = connection.execute(
                "SELECT metadata_json FROM claims WHERE run_id = ?", (run_id,)
            ).fetchall()
        observed_slots: set[str] = set()
        for row in (*evidence_rows, *claim_rows):
            metadata = _metadata(row["metadata_json"])
            slots = metadata.get("evidence_slots", ())
            if isinstance(slots, str):
                slots = (slots,)
            if isinstance(slots, (list, tuple, set)):
                observed_slots.update(
                    slot.strip()
                    for slot in slots
                    if isinstance(slot, str) and slot.strip()
                )
            single_slot = metadata.get("evidence_slot")
            if isinstance(single_slot, str) and single_slot.strip():
                observed_slots.add(single_slot.strip())
        required = contract["evidence_slots"]
        covered = [slot for slot in required if slot in observed_slots]
        missing = [slot for slot in required if slot not in observed_slots]
        return {
            "required": required,
            "covered": covered,
            "missing": missing,
            "required_count": len(required),
            "covered_count": len(covered),
            "complete": not missing,
        }

    def save_source(self, source: Source | None = None, **fields: Any) -> Source:
        if source is None:
            source = Source(**fields)
        elif fields:
            raise TypeError("Pass either a Source or keyword fields, not both")

        source = replace(source, metadata=sanitize_untrusted_metadata(source.metadata))

        if source.parent_source_id:
            parent = self.get_source(source.parent_source_id)
            if parent is None:
                raise KeyError(f"Parent source not found: {source.parent_source_id}")
            if parent.run_id != source.run_id:
                raise ValueError("Parent source must belong to the same research run")
            root_id = source.root_source_id or parent.root_source_id or parent.id
        else:
            root_id = source.root_source_id or source.id
        source = replace(source, root_source_id=root_id)

        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO sources
                   (id, run_id, url, title, publisher, published_at, accessed_at,
                    source_type, parent_source_id, root_source_id, provenance_status, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    run_id=excluded.run_id, url=excluded.url, title=excluded.title,
                    publisher=excluded.publisher, published_at=excluded.published_at,
                    accessed_at=excluded.accessed_at, source_type=excluded.source_type,
                    parent_source_id=excluded.parent_source_id, root_source_id=excluded.root_source_id,
                    provenance_status=excluded.provenance_status,
                    metadata_json=excluded.metadata_json""",
                (
                    source.id,
                    source.run_id,
                    source.url,
                    source.title,
                    source.publisher,
                    source.published_at,
                    source.accessed_at,
                    _value(source.source_type),
                    source.parent_source_id,
                    source.root_source_id,
                    _value(source.provenance_status),
                    _metadata_json(source.metadata),
                ),
            )
        return source

    def get_source(self, source_id: str) -> Source | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            return None
        return Source(
            id=row["id"],
            run_id=row["run_id"],
            url=row["url"],
            title=row["title"],
            publisher=row["publisher"],
            published_at=row["published_at"],
            accessed_at=row["accessed_at"],
            source_type=_enum(SourceType, row["source_type"]),
            parent_source_id=row["parent_source_id"],
            root_source_id=row["root_source_id"],
            provenance_status=_enum(ProvenanceStatus, row["provenance_status"]),
            metadata=sanitize_untrusted_metadata(_metadata(row["metadata_json"])),
        )

    def save_evidence(self, evidence: Evidence | None = None, **fields: Any) -> Evidence:
        if evidence is None:
            evidence = Evidence(**fields)
        elif fields:
            raise TypeError("Pass either an Evidence or keyword fields, not both")

        evidence = replace(
            evidence, metadata=sanitize_untrusted_metadata(evidence.metadata)
        )

        source = self.get_source(evidence.source_id)
        if source is None:
            raise KeyError(f"Source not found: {evidence.source_id}")
        if source.run_id != evidence.run_id:
            raise ValueError("Evidence and source must belong to the same research run")
        evidence = replace(evidence, root_source_id=evidence.root_source_id or source.root_source_id)

        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO evidence
                   (id, run_id, source_id, root_source_id, quote, locator, observed_at,
                    metric, value, unit, market, period_start, period_end, scope, method,
                    source_mode, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    run_id=excluded.run_id, source_id=excluded.source_id,
                    root_source_id=excluded.root_source_id, quote=excluded.quote,
                    locator=excluded.locator, observed_at=excluded.observed_at,
                    metric=excluded.metric, value=excluded.value,
                    unit=excluded.unit, market=excluded.market,
                    period_start=excluded.period_start, period_end=excluded.period_end,
                    scope=excluded.scope, method=excluded.method,
                    source_mode=excluded.source_mode, metadata_json=excluded.metadata_json""",
                (
                    evidence.id,
                    evidence.run_id,
                    evidence.source_id,
                    evidence.root_source_id,
                    evidence.quote,
                    evidence.locator,
                    evidence.observed_at,
                    evidence.metric,
                    None if evidence.value is None else str(evidence.value),
                    evidence.unit,
                    evidence.market,
                    evidence.period_start,
                    evidence.period_end,
                    evidence.scope,
                    evidence.method,
                    _value(evidence.source_mode),
                    _metadata_json(evidence.metadata),
                ),
            )
        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE id = ?", (evidence_id,)
            ).fetchone()
        if row is None:
            return None
        return Evidence(
            id=row["id"],
            run_id=row["run_id"],
            source_id=row["source_id"],
            root_source_id=row["root_source_id"],
            quote=row["quote"],
            locator=row["locator"],
            observed_at=row["observed_at"],
            metric=row["metric"],
            value=row["value"],
            unit=row["unit"],
            market=row["market"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            scope=row["scope"],
            method=row["method"],
            source_mode=_enum(SourceMode, row["source_mode"]),
            metadata=sanitize_untrusted_metadata(_metadata(row["metadata_json"])),
        )

    def save_store_chart_snapshot(
        self, snapshot: StoreChartSnapshot
    ) -> StoreChartSnapshot:
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO store_snapshots
                   (id, run_id, provider, store, country, chart_type, observed_at,
                    source_mode, source_url, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.snapshot_id,
                    snapshot.run_id,
                    snapshot.provider,
                    snapshot.store,
                    snapshot.country,
                    snapshot.chart_type,
                    snapshot.observed_at,
                    _value(snapshot.source_mode),
                    snapshot.source_url,
                    _metadata_json(snapshot.metadata),
                ),
            )
            connection.executemany(
                """INSERT INTO store_snapshot_items
                   (snapshot_id, game_id, store_app_id, title, rank, genre, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        snapshot.snapshot_id,
                        item.game_id,
                        item.store_app_id,
                        item.title,
                        item.rank,
                        item.genre,
                        _metadata_json(item.metadata),
                    )
                    for item in snapshot.items
                ],
            )
        return snapshot

    def list_store_chart_history(
        self,
        *,
        run_id: str,
        store: str,
        country: str,
        chart_type: str,
        game_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(store, str) or not store.strip():
            raise ValueError("store must be a non-empty string")
        if not isinstance(country, str) or not country.strip():
            raise ValueError("country must be a non-empty string")
        if not isinstance(chart_type, str) or not chart_type.strip():
            raise ValueError("chart_type must be a non-empty string")
        if not isinstance(game_id, str) or not game_id.strip():
            raise ValueError("game_id must be a non-empty string")
        conditions = [
            "s.run_id = ?",
            "s.store = ?",
            "s.country = ?",
            "s.chart_type = ?",
            "i.game_id = ?",
        ]
        values: list[Any] = [
            run_id,
            store.strip().casefold(),
            country.strip().upper(),
            chart_type.strip(),
            game_id.strip(),
        ]
        if start is not None:
            conditions.append("s.observed_at >= ?")
            values.append(start)
        if end is not None:
            conditions.append("s.observed_at <= ?")
            values.append(end)
        query = f"""SELECT s.id AS snapshot_id, s.provider, s.store, s.country,
                          s.chart_type, s.observed_at, s.source_mode, s.source_url,
                          s.metadata_json AS snapshot_metadata_json,
                          i.game_id, i.store_app_id, i.title, i.rank, i.genre,
                          i.metadata_json AS item_metadata_json
                   FROM store_snapshots AS s
                   JOIN store_snapshot_items AS i ON i.snapshot_id = s.id
                   WHERE {' AND '.join(conditions)}
                   ORDER BY s.observed_at ASC, s.id ASC"""
        with self.database.connection() as connection:
            rows = connection.execute(query, values).fetchall()
        return [
            {
                "snapshot_id": row["snapshot_id"],
                "provider": row["provider"],
                "store": row["store"],
                "country": row["country"],
                "chart_type": row["chart_type"],
                "observed_at": row["observed_at"],
                "source_mode": row["source_mode"],
                "source_url": row["source_url"],
                "snapshot_metadata": _metadata(row["snapshot_metadata_json"]),
                "game_id": row["game_id"],
                "store_app_id": row["store_app_id"],
                "title": row["title"],
                "rank": int(row["rank"]),
                "genre": row["genre"],
                "metadata": _metadata(row["item_metadata_json"]),
            }
            for row in rows
        ]

    def save_claim(self, claim: Claim | None = None, **fields: Any) -> Claim:
        if claim is None:
            claim = Claim(**fields)
        elif fields:
            raise TypeError("Pass either a Claim or keyword fields, not both")
        claim = replace(claim, target_metric=normalize_metric(claim.target_metric))
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO claims
                   (id, run_id, text, claim_type, target_metric, status, confidence_level,
                    confidence_rationale, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    run_id=excluded.run_id, text=excluded.text,
                    claim_type=excluded.claim_type, target_metric=excluded.target_metric,
                    status=excluded.status,
                    confidence_level=excluded.confidence_level,
                    confidence_rationale=excluded.confidence_rationale,
                    metadata_json=excluded.metadata_json""",
                (
                    claim.id,
                    claim.run_id,
                    claim.text,
                    _value(claim.claim_type),
                    claim.target_metric,
                    _value(claim.status),
                    _value(claim.confidence_level),
                    claim.confidence_rationale,
                    _metadata_json(claim.metadata),
                ),
            )
        return claim

    def get_claim(self, claim_id: str) -> Claim | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        return self._claim_from_row(row) if row is not None else None

    def list_claims(self, run_id: str) -> list[Claim]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM claims WHERE run_id = ? ORDER BY rowid", (run_id,)
            ).fetchall()
        return [self._claim_from_row(row) for row in rows]

    @staticmethod
    def _claim_from_row(row: sqlite3.Row) -> Claim:
        return Claim(
            id=row["id"],
            run_id=row["run_id"],
            text=row["text"],
            claim_type=_enum(ClaimType, row["claim_type"]),
            status=_enum(ClaimStatus, row["status"]),
            confidence_level=_enum(ConfidenceLevel, row["confidence_level"]),
            confidence_rationale=row["confidence_rationale"],
            target_metric=row["target_metric"],
            metadata=_metadata(row["metadata_json"]),
        )

    def update_claim_validation(
        self,
        claim_id: str,
        status: ClaimStatus | str,
        confidence_level: ConfidenceLevel | str,
        confidence_rationale: str | None,
    ) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE claims
                   SET status = ?, confidence_level = ?, confidence_rationale = ?
                   WHERE id = ?""",
                (_value(status), _value(confidence_level), confidence_rationale, claim_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Claim not found: {claim_id}")

    def backfill_claim_target_metric(self, claim_id: str, target_metric: str) -> None:
        normalized_metric = normalize_metric(target_metric)
        if normalized_metric is None:
            raise ValueError("target_metric is required for metric repair")
        with self.database.transaction() as connection:
            claim = connection.execute(
                "SELECT target_metric FROM claims WHERE id = ?", (claim_id,)
            ).fetchone()
            if claim is None:
                raise KeyError(f"Claim not found: {claim_id}")
            if claim["target_metric"] is not None:
                raise ValueError("Only claims with a null target_metric can be repaired")
            evidence = connection.execute(
                """SELECT e.metric FROM claim_evidence ce
                   JOIN evidence e ON e.id = ce.evidence_id
                   WHERE ce.claim_id = ? AND e.metric IS NOT NULL""",
                (claim_id,),
            ).fetchall()
            if not evidence:
                raise ValueError("Metric repair requires linked evidence with a metric")
            if any(normalize_metric(row["metric"]) != normalized_metric for row in evidence):
                raise ValueError("All linked evidence metrics must match target_metric")
            connection.execute(
                "UPDATE claims SET target_metric = ? WHERE id = ? AND target_metric IS NULL",
                (normalized_metric, claim_id),
            )

    def link_claim_evidence(
        self,
        claim_id: str,
        evidence_id: str,
        relation: EvidenceRelation | str = EvidenceRelation.SUPPORTS,
    ) -> ClaimEvidence:
        with self.database.transaction() as connection:
            claim = connection.execute(
                "SELECT run_id FROM claims WHERE id = ?", (claim_id,)
            ).fetchone()
            evidence = connection.execute(
                "SELECT run_id FROM evidence WHERE id = ?", (evidence_id,)
            ).fetchone()
            if claim is None:
                raise KeyError(f"Claim not found: {claim_id}")
            if evidence is None:
                raise KeyError(f"Evidence not found: {evidence_id}")
            if claim["run_id"] != evidence["run_id"]:
                raise ValueError("Claim and evidence must belong to the same research run")
            connection.execute(
                """INSERT OR IGNORE INTO claim_evidence (claim_id, evidence_id, relation)
                   VALUES (?, ?, ?)""",
                (claim_id, evidence_id, _value(relation)),
            )
        return ClaimEvidence(claim_id=claim_id, evidence_id=evidence_id, relation=relation)

    def save_issue(self, issue: ResearchIssue | None = None, **fields: Any) -> ResearchIssue:
        if issue is None:
            issue = ResearchIssue(**fields)
        elif fields:
            raise TypeError("Pass either a ResearchIssue or keyword fields, not both")
        with self.database.transaction() as connection:
            related_entities = (
                ("claim", "claims", issue.related_claim_id),
                ("source", "sources", issue.source_id),
                ("evidence", "evidence", issue.evidence_id),
            )
            for kind, table, entity_id in related_entities:
                if entity_id:
                    row = connection.execute(
                        f"SELECT run_id FROM {table} WHERE id = ?", (entity_id,)
                    ).fetchone()
                    if row is None:
                        raise KeyError(f"{kind.title()} not found: {entity_id}")
                    if row["run_id"] != issue.run_id:
                        raise ValueError(f"Issue and {kind} must belong to the same research run")
            connection.execute(
                """INSERT INTO research_issues
                   (id, run_id, code, message, severity, status, related_claim_id,
                    source_id, evidence_id, created_at, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    run_id=excluded.run_id, code=excluded.code, message=excluded.message,
                    severity=excluded.severity, status=excluded.status,
                    related_claim_id=excluded.related_claim_id,
                    source_id=excluded.source_id, evidence_id=excluded.evidence_id,
                    created_at=excluded.created_at, metadata_json=excluded.metadata_json""",
                (
                    issue.id,
                    issue.run_id,
                    issue.code,
                    issue.message,
                    _value(issue.severity),
                    _value(issue.status),
                    issue.related_claim_id,
                    issue.source_id,
                    issue.evidence_id,
                    issue.created_at,
                    _metadata_json(issue.metadata),
                ),
            )
        return issue

    def list_issues(self, run_id: str) -> list[ResearchIssue]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM research_issues WHERE run_id = ? ORDER BY rowid", (run_id,)
            ).fetchall()
        return [
            ResearchIssue(
                id=row["id"],
                run_id=row["run_id"],
                code=row["code"],
                message=row["message"],
                severity=_enum(IssueSeverity, row["severity"]),
                status=_enum(IssueStatus, row["status"]),
                related_claim_id=row["related_claim_id"],
                source_id=row["source_id"],
                evidence_id=row["evidence_id"],
                created_at=row["created_at"],
                metadata=_metadata(row["metadata_json"]),
            )
            for row in rows
        ]

    def update_issue_status(self, issue_id: str, status: IssueStatus | str) -> None:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                "UPDATE research_issues SET status = ? WHERE id = ?",
                (_value(status), issue_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Research issue not found: {issue_id}")

    def get_claim_trace(self, claim_id: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            claim_row = connection.execute(
                "SELECT * FROM claims WHERE id = ?", (claim_id,)
            ).fetchone()
            if claim_row is None:
                return None
            rows = connection.execute(
                """SELECT ce.relation,
                          e.id AS evidence_id, e.run_id AS evidence_run_id,
                          e.source_id, e.root_source_id AS evidence_root_source_id,
                          e.quote, e.locator, e.observed_at, e.metric, e.unit,
                          e.value, e.market, e.period_start, e.period_end, e.scope, e.method,
                          e.source_mode, e.metadata_json AS evidence_metadata_json,
                          s.id AS source_id_value, s.run_id AS source_run_id,
                          s.url, s.title, s.publisher, s.published_at, s.accessed_at,
                          s.source_type, s.parent_source_id, s.root_source_id,
                          s.provenance_status, s.metadata_json AS source_metadata_json
                   FROM claim_evidence ce
                   JOIN evidence e ON e.id = ce.evidence_id
                   JOIN sources s ON s.id = e.source_id
                   WHERE ce.claim_id = ?
                   ORDER BY e.id, ce.relation""",
                (claim_id,),
            ).fetchall()

        claim = dict(claim_row)
        claim["metadata"] = _metadata(claim.pop("metadata_json"))
        evidence_items = []
        for row in rows:
            evidence = {
                "id": row["evidence_id"],
                "run_id": row["evidence_run_id"],
                "source_id": row["source_id"],
                "root_source_id": row["evidence_root_source_id"],
                "quote": row["quote"],
                "locator": row["locator"],
                "observed_at": row["observed_at"],
                "metric": row["metric"],
                "value": row["value"],
                "unit": row["unit"],
                "market": row["market"],
                "period_start": row["period_start"],
                "period_end": row["period_end"],
                "scope": row["scope"],
                "method": row["method"],
                "source_mode": row["source_mode"],
                "metadata": sanitize_untrusted_metadata(
                    _metadata(row["evidence_metadata_json"])
                ),
            }
            source = {
                "id": row["source_id_value"],
                "run_id": row["source_run_id"],
                "url": row["url"],
                "title": row["title"],
                "publisher": row["publisher"],
                "published_at": row["published_at"],
                "accessed_at": row["accessed_at"],
                "source_type": row["source_type"],
                "parent_source_id": row["parent_source_id"],
                "root_source_id": row["root_source_id"],
                "provenance_status": row["provenance_status"],
                "metadata": sanitize_untrusted_metadata(
                    _metadata(row["source_metadata_json"])
                ),
            }
            evidence_items.append(
                {
                    "relation": row["relation"],
                    "evidence": evidence,
                    "source": source,
                    "source_assurance": source_assurance_for_host_supplied_source(),
                }
            )
        return {"claim": claim, "evidence": evidence_items}

    def get_claim_lineage_audit(self, claim_id: str) -> dict[str, Any] | None:
        trace = self.get_claim_trace(claim_id)
        if trace is None:
            return None
        run_id = trace["claim"]["run_id"]
        with self.database.connection() as connection:
            rows = connection.execute(
                """SELECT id, parent_source_id, root_source_id
                   FROM sources WHERE run_id = ? ORDER BY id""",
                (run_id,),
            ).fetchall()
        run_sources = [dict(row) for row in rows]
        return build_claim_lineage_audit(trace, run_sources)
