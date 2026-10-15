from __future__ import annotations

from collections import defaultdict
from typing import Any


def _root_id(source: dict[str, Any], evidence: dict[str, Any] | None = None) -> str:
    evidence = evidence or {}
    return (
        evidence.get("root_source_id")
        or source.get("root_source_id")
        or source["id"]
    )


def build_claim_lineage_audit(
    claim_trace: dict[str, Any], run_sources: list[dict[str, Any]]
) -> dict[str, Any]:
    """Build a stable, structured evidence → document → origin audit."""
    evidence_by_id: dict[str, dict[str, Any]] = {}
    source_by_id: dict[str, dict[str, Any]] = {}
    relations_by_evidence: dict[str, set[str]] = defaultdict(set)
    roots: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"evidence_ids": set(), "supporting_evidence_ids": set()}
    )
    edges: list[dict[str, str]] = []

    for source in run_sources:
        source_by_id[source["id"]] = source

    for item in claim_trace["evidence"]:
        evidence = item["evidence"]
        source = item["source"]
        evidence_id = evidence["id"]
        source_id = source["id"]
        relation = str(item["relation"])
        root_source_id = _root_id(source, evidence)
        evidence_by_id[evidence_id] = evidence
        relations_by_evidence[evidence_id].add(relation)
        roots[root_source_id]["evidence_ids"].add(evidence_id)
        if relation == "SUPPORTS":
            roots[root_source_id]["supporting_evidence_ids"].add(evidence_id)
        edge = {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "root_source_id": root_source_id,
            "relation": relation,
        }
        if edge not in edges:
            edges.append(edge)

    document_ids = {item["source"]["id"] for item in claim_trace["evidence"]}
    all_root_ids = set(roots)
    supporting_root_ids = {
        root_id
        for root_id, values in roots.items()
        if values["supporting_evidence_ids"]
    }
    root_sources = []
    for root_source_id in sorted(roots):
        descendants = sorted(
            source_id
            for source_id, source in source_by_id.items()
            if (source.get("root_source_id") or source_id) == root_source_id
        )
        if root_source_id not in descendants and root_source_id in source_by_id:
            descendants.append(root_source_id)
            descendants.sort()
        root_sources.append(
            {
                "root_source_id": root_source_id,
                "evidence_ids": sorted(roots[root_source_id]["evidence_ids"]),
                "supporting_evidence_ids": sorted(
                    roots[root_source_id]["supporting_evidence_ids"]
                ),
                "descendant_source_ids": descendants,
            }
        )

    return {
        "claim": claim_trace["claim"],
        "evidence_count": len(evidence_by_id),
        "document_count": len(document_ids),
        "independent_root_count": len(all_root_ids),
        "supporting_evidence_count": sum(
            1 for relations in relations_by_evidence.values() if "SUPPORTS" in relations
        ),
        "supporting_independent_root_count": len(supporting_root_ids),
        "root_sources": root_sources,
        "edges": sorted(
            edges,
            key=lambda edge: (
                edge["evidence_id"], edge["source_id"], edge["relation"]
            ),
        ),
    }
