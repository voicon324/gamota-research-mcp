from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .enums import ClaimType, RunStatus
from .repository import ResearchRepository


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,119}$")
_CONFIDENCE = {
    "STRONG": "high",
    "MODERATE": "medium",
    "WEAK": "low",
    "INSUFFICIENT": "low",
    "UNASSESSED": "low",
}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:80].strip("-") or "game-report"


def _enum(value: Any) -> str:
    return str(getattr(value, "value", value))


def _typed_value(value: Any) -> Any:
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip()):
        return value
    number = float(value) if "." in value else int(value)
    return int(number) if isinstance(number, float) and number.is_integer() else number


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def validate_game_decision_brief(report: dict[str, Any]) -> list[str]:
    """Validate the public v1 report contract and all claim/evidence references."""
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if report.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    metadata = report.get("report")
    if not isinstance(metadata, dict):
        errors.append("report metadata is required")
        metadata = {}
    for field in ("id", "title", "game", "as_of", "research_run_id"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            errors.append(f"report.{field} is required")
    if metadata.get("type") != "game_decision_brief":
        errors.append("report.type must be 'game_decision_brief'")
    if metadata.get("status") != "published":
        errors.append("report.status must be 'published'")

    scope = report.get("scope")
    if not isinstance(scope, dict) or not isinstance(scope.get("question"), str) or not scope["question"].strip():
        errors.append("scope.question is required")

    summary = report.get("summary")
    if not isinstance(summary, dict) or not isinstance(summary.get("verdict"), str) or not summary["verdict"].strip():
        errors.append("summary.verdict is required")
    elif summary.get("confidence") not in {"high", "medium", "low"}:
        errors.append("summary.confidence must be high, medium, or low")

    evidence = report.get("evidence")
    evidence_items = evidence if isinstance(evidence, list) else []
    evidence_ids = {item.get("id") for item in evidence_items if isinstance(item, dict)}
    source_ids = {
        item.get("id") for item in report.get("sources", []) if isinstance(item, dict)
    }
    for item in evidence_items:
        if not isinstance(item, dict):
            errors.append("evidence items must be objects")
            continue
        if item.get("source_id") not in source_ids:
            errors.append(f"evidence {item.get('id')} references missing source {item.get('source_id')}")

    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        findings = []
    for index, finding in enumerate(findings):
        prefix = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not isinstance(finding.get("statement"), str) or not finding["statement"].strip():
            errors.append(f"{prefix}.statement is required")
        if finding.get("type") not in {"fact", "estimate", "inference"}:
            errors.append(f"{prefix}.type must be fact, estimate, or inference")
        if finding.get("confidence") not in {"high", "medium", "low"}:
            errors.append(f"{prefix}.confidence must be high, medium, or low")
        if finding.get("type") == "inference" and finding.get("confidence") == "high":
            errors.append(f"{prefix} inference confidence cannot be high")
        if not isinstance(finding.get("evidence_ids"), list) or not finding["evidence_ids"]:
            errors.append(f"{prefix}.evidence_ids must contain at least one evidence ID")
        else:
            for evidence_id in finding["evidence_ids"]:
                if evidence_id not in evidence_ids:
                    errors.append(f"{prefix} references missing evidence {evidence_id}")

    for index, recommendation in enumerate(report.get("recommendations", [])):
        if not isinstance(recommendation, dict) or not str(recommendation.get("text", "")).strip():
            errors.append(f"recommendations[{index}].text is required")
            continue
        refs = recommendation.get("evidence_ids", [])
        if not isinstance(refs, list) or any(ref not in evidence_ids for ref in refs):
            errors.append(f"recommendations[{index}] references missing evidence")
    for index, metric in enumerate(report.get("metrics", [])):
        refs = metric.get("evidence_ids", []) if isinstance(metric, dict) else []
        if not isinstance(refs, list) or not refs or any(ref not in evidence_ids for ref in refs):
            errors.append(f"metrics[{index}] references missing evidence")
    return errors


def render_report_markdown(report: dict[str, Any]) -> str:
    metadata = report["report"]
    scope = report["scope"]
    summary = report["summary"]
    lines = [
        f"# {metadata['title']}",
        "",
        f"- **Game:** {metadata['game']}",
        f"- **As of:** {metadata['as_of']}",
        f"**Confidence:** {summary['confidence']}",
        "",
        "## Research question",
        "",
        scope["question"],
        "",
        "## Executive verdict",
        "",
        summary["verdict"],
        "",
        "## Scope",
        "",
        f"- Markets: {', '.join(scope.get('markets', [])) or 'Not specified'}",
        f"- Platforms: {', '.join(scope.get('platforms', [])) or 'Not specified'}",
        f"- Period: {scope.get('period') or 'Not specified'}",
        "",
        "## Findings",
        "",
    ]
    for finding in report["findings"]:
        lines.extend([
            f"### {finding['statement']}",
            "",
            f"{finding['type'].title()} · {finding['confidence']} confidence · evidence: {', '.join(finding['evidence_ids'])}",
            "",
        ])
    lines.extend(["## Market signals", ""])
    if report.get("metrics"):
        for metric in report["metrics"]:
            lines.append(
                f"- **{metric['metric']}**: {metric['value']} {metric.get('unit') or ''} "
                f"({metric['data_type']}; {metric.get('market') or 'market not specified'}; "
                f"{metric.get('period') or 'period not specified'}; {len(metric['evidence_ids'])} evidence item(s))"
            )
    else:
        lines.append("No scoped numeric or categorical market signals were recorded.")
    lines.append("")
    lines.extend(["## Recommendations", ""])
    if report["recommendations"]:
        lines.extend(
            f"- {item['text']} (evidence: {', '.join(item.get('evidence_ids', [])) or 'not linked'})"
            for item in report["recommendations"]
        )
    else:
        lines.append("No evidence-linked recommendations were recorded.")
    lines.extend(["", "## Unknowns and issues", ""])
    if report["unknowns"]:
        lines.extend(f"- {item['description']}" for item in report["unknowns"])
    else:
        lines.append("No open unknowns were recorded.")
    lines.extend(["", "## Sources and evidence", ""])
    source_map = {source["id"]: source for source in report["sources"]}
    for item in report["evidence"]:
        source = source_map[item["source_id"]]
        lines.extend([
            f"- **{source.get('title') or source['url']}** — {item['excerpt']}",
            f"  - [{source['url']}]({source['url']}); accessed {source.get('accessed_at') or 'date unknown'}; locator: {item.get('locator') or 'not specified'}",
        ])
    lines.extend(["", "## Methodology", "", "Research conducted by the host agent using its native search/fetch tools. The MCP records claims and evidence and applies deterministic validation; it does not perform general web search or infer causality.", ""])
    return "\n".join(lines)


class ReportService:
    """Compile validated research state into immutable, web-readable report artifacts."""

    def __init__(self, repository: ResearchRepository, output_dir: str | Path):
        self.repository = repository
        self.output_dir = Path(output_dir).expanduser().resolve()

    def publish_game_decision_brief(
        self,
        *,
        run_id: str,
        title: str,
        game: str,
        verdict: str,
        platforms: list[str] | None = None,
        markets: list[str] | None = None,
    ) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Research run not found: {run_id}")
        if run.finalized_at is None or _enum(run.status) not in {
            RunStatus.COMPLETE.value,
            RunStatus.PARTIAL.value,
            RunStatus.INSUFFICIENT_DATA.value,
        }:
            raise ValueError("Research run must be finalized before publishing a report")
        for field, value in (("title", title), ("game", game), ("verdict", verdict)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")

        contract = self.repository.get_research_contract(run_id) or {"question": run.question}
        period = contract.get("time_scope")
        if isinstance(period, dict):
            period = dict(period)
        trace_by_claim: dict[str, dict[str, Any]] = {}
        for claim in self.repository.list_claims(run_id):
            trace = self.repository.get_claim_trace(claim.id)
            if trace:
                trace_by_claim[claim.id] = trace

        all_evidence: dict[str, dict[str, Any]] = {}
        all_sources: dict[str, dict[str, Any]] = {}
        findings: list[dict[str, Any]] = []
        recommendations: list[dict[str, Any]] = []
        unknowns: list[dict[str, Any]] = []
        for issue in self.repository.list_issues(run_id):
            if _enum(issue.status) == "OPEN":
                unknowns.append({
                    "id": issue.id,
                    "type": issue.code,
                    "severity": _enum(issue.severity),
                    "description": issue.message,
                    "related_claim_id": issue.related_claim_id,
                })

        for claim_id, trace in trace_by_claim.items():
            claim = trace["claim"]
            claim_type = _enum(claim["claim_type"])
            links = trace["evidence"]
            claim_evidence_ids: list[str] = []
            for link in links:
                evidence = link["evidence"]
                source = link["source"]
                evidence_id = evidence["id"]
                claim_evidence_ids.append(evidence_id)
                all_sources[source["id"]] = {
                    "id": source["id"],
                    "url": source["url"],
                    "title": source["title"],
                    "publisher": source["publisher"],
                    "published_at": source["published_at"],
                    "accessed_at": source["accessed_at"],
                    "provenance_status": source["provenance_status"],
                    "root_source_id": source["root_source_id"],
                }
                item = all_evidence.setdefault(evidence_id, {
                    "id": evidence_id,
                    "source_id": source["id"],
                    "excerpt": evidence["quote"],
                    "locator": evidence["locator"],
                    "retrieved_at": evidence["observed_at"] or source["accessed_at"],
                    "metric": evidence["metric"],
                    "value": _typed_value(evidence["value"]),
                    "unit": evidence["unit"],
                    "market": evidence["market"],
                    "period_start": evidence["period_start"],
                    "period_end": evidence["period_end"],
                    "scope": evidence["scope"],
                    "method": evidence["method"],
                    "source_mode": evidence["source_mode"],
                    "data_type": "estimate" if claim_type == ClaimType.ESTIMATE.value else (
                        "proxy" if _enum(evidence["source_mode"]) == "PROXY" else "reported"
                    ),
                    "validation": "supported" if _enum(claim["status"]) == "VALID" else "partial",
                    "claim_ids": [],
                })
                if claim_type == ClaimType.ESTIMATE.value:
                    item["data_type"] = "estimate"
                if _enum(link["relation"]) == "CONTRADICTS":
                    item["validation"] = "conflicting"
                if claim_id not in item["claim_ids"]:
                    item["claim_ids"].append(claim_id)

            if _enum(claim["status"]) != "VALID":
                unknowns.append({
                    "id": f"claim-{claim_id}",
                    "type": "INVALID_CLAIM",
                    "severity": "WARNING",
                    "description": f"Excluded from findings because validation status is {_enum(claim['status'])}: {claim['text']}",
                    "related_claim_id": claim_id,
                })
                continue
            confidence = _CONFIDENCE.get(_enum(claim["confidence_level"]), "low")
            if claim_type == ClaimType.RECOMMENDATION.value:
                recommendations.append({
                    "id": claim_id,
                    "text": claim["text"],
                    "confidence": confidence,
                    "evidence_ids": claim_evidence_ids,
                })
            else:
                assertion_type = str(claim.get("metadata", {}).get("assertion_type", "")).casefold()
                finding_type = "estimate" if (
                    claim_type == ClaimType.ESTIMATE.value or assertion_type == "estimate"
                ) else (
                    "inference" if claim_type == ClaimType.INFERENCE.value else "fact"
                )
                if finding_type == "inference" and confidence == "high":
                    confidence = "medium"
                findings.append({
                    "id": claim_id,
                    "statement": claim["text"],
                    "type": finding_type,
                    "confidence": confidence,
                    "evidence_ids": claim_evidence_ids,
                    "validation": _enum(claim["status"]).casefold(),
                    "implication": claim.get("metadata", {}).get("implication"),
                })

        coverage = self.repository.get_research_evidence_slot_coverage(run_id)
        for slot in coverage.get("missing", []):
            unknowns.append({
                "id": f"missing-slot-{_slug(slot)}",
                "type": "MISSING_EVIDENCE_SLOT",
                "severity": "BLOCKING",
                "description": f"Required evidence slot was not covered: {slot}",
            })

        published_on = datetime.now(timezone.utc).date().isoformat()
        identity = json.dumps(
            {
                "run_id": run_id,
                "title": title.strip(),
                "game": game.strip(),
                "verdict": verdict.strip(),
                "markets": markets if markets is not None else contract.get("geography", []),
                "platforms": platforms or [],
                "as_of": published_on,
                "question": contract.get("question", run.question),
                "findings": findings,
                "recommendations": recommendations,
                "unknowns": unknowns,
                "sources": list(all_sources.values()),
                "evidence": list(all_evidence.values()),
                "metrics": self._market_signals(all_evidence),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8]
        identifier = f"{_slug(game)}-{_slug(title)}-{run_id[:8].lower()}-{digest}"[:120].strip("-")
        report = {
            "schema_version": "1.0",
            "report": {
                "id": identifier,
                "type": "game_decision_brief",
                "title": title.strip(),
                "game": game.strip(),
                "as_of": published_on,
                "status": "published",
                "research_run_id": run_id,
                "research_status": _enum(run.status),
                "created_at": run.created_at,
                "finalized_at": run.finalized_at,
            },
            "scope": {
                "question": contract.get("question", run.question),
                "decision_goal": contract.get("decision_goal"),
                "period": period,
                "markets": markets if markets is not None else contract.get("geography", []),
                "platforms": platforms or [],
                "assumptions": contract.get("assumptions", []),
            },
            "summary": {
                "verdict": verdict.strip(),
                "confidence": _CONFIDENCE.get(self._run_confidence(run_id), "low"),
            },
            "findings": findings,
            "recommendations": recommendations,
            "unknowns": unknowns,
            "metrics": self._market_signals(all_evidence),
            "sources": list(all_sources.values()),
            "evidence": list(all_evidence.values()),
        }
        errors = validate_game_decision_brief(report)
        if errors:
            raise ValueError("Report validation failed: " + "; ".join(errors))
        markdown = render_report_markdown(report)
        self._write_published(report, markdown)
        return report

    def _run_confidence(self, run_id: str) -> str:
        confidence_values = [
            _enum(claim.confidence_level)
            for claim in self.repository.list_claims(run_id)
            if _enum(claim.status) == "VALID"
        ]
        if not confidence_values:
            return "INSUFFICIENT"
        rank = {"STRONG": 3, "MODERATE": 2, "WEAK": 1, "UNASSESSED": 0, "INSUFFICIENT": 0}
        return min(confidence_values, key=lambda value: rank.get(value, 0))

    @staticmethod
    def _market_signals(evidence_items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
        for evidence in evidence_items.values():
            if not evidence["metric"] or evidence["value"] is None:
                continue
            period = (
                f"{evidence['period_start'] or '?'} to {evidence['period_end'] or '?'}"
                if evidence["period_start"] or evidence["period_end"]
                else None
            )
            key = (
                evidence["metric"], str(evidence["value"]), evidence["unit"],
                evidence["data_type"], evidence["market"], period,
            )
            signal = grouped.setdefault(key, {
                "metric": evidence["metric"],
                "value": evidence["value"],
                "unit": evidence["unit"],
                "data_type": evidence["data_type"],
                "market": evidence["market"],
                "period": period,
                "scope": evidence["scope"],
                "evidence_ids": [],
            })
            signal["evidence_ids"].append(evidence["id"])
        return list(grouped.values())

    def _write_published(self, report: dict[str, Any], markdown: str) -> None:
        report_id = report["report"]["id"]
        if not _ID_RE.fullmatch(report_id):
            raise ValueError("Generated report ID contains unsupported characters")
        report_dir = self.output_dir / report_id
        report_path = report_dir / "report.json"
        markdown_path = report_dir / "report.md"
        if report_path.exists():
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            if existing != report:
                raise ValueError(f"Published report is immutable: {report_id}")
            return
        manifest_path = self.output_dir / "index.json"
        manifest = {"schema_version": "1.0", "reports": []}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        row = {
            "id": report_id,
            "title": report["report"]["title"],
            "game": report["report"]["game"],
            "as_of": report["report"]["as_of"],
            "confidence": report["summary"]["confidence"],
            "research_status": report["report"]["research_status"],
            "path": f"./{report_id}/report.json",
        }
        manifest["reports"] = [
            item for item in manifest.get("reports", []) if item.get("id") != report_id
        ] + [row]
        manifest["reports"].sort(key=lambda item: item.get("as_of", ""), reverse=True)
        _atomic_write(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        _atomic_write(markdown_path, markdown)
        _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    def list_reports(self) -> dict[str, Any]:
        path = self.output_dir / "index.json"
        if not path.exists():
            return {"schema_version": "1.0", "reports": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def get_report(self, report_id: str) -> dict[str, Any]:
        if not _ID_RE.fullmatch(report_id):
            raise ValueError("report_id contains unsupported characters")
        path = self.output_dir / report_id / "report.json"
        if not path.is_file():
            raise KeyError(f"Published report not found: {report_id}")
        report = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_game_decision_brief(report)
        if errors:
            raise ValueError("Stored report is invalid: " + "; ".join(errors))
        return report
