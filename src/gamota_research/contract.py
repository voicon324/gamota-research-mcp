from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping


def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = [value]
    else:
        values = list(value)
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} must contain non-empty strings")
        clean = item.strip()
        if clean not in normalized:
            normalized.append(clean)
    return tuple(normalized)


@dataclass(frozen=True)
class ResearchContract:
    question: str
    decision_goal: str | None = None
    geography: tuple[str, ...] = ()
    time_scope: str | dict[str, Any] | None = None
    metrics: tuple[str, ...] = ()
    segments: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    evidence_slots: tuple[str, ...] = ()
    freshness_cutoff: str | None = None
    planned_query_budget: int = 10
    domain_tool_budget: int = 10
    research_round_budget: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("question must be a non-empty string")
        object.__setattr__(self, "question", self.question.strip())
        for field_name in (
            "geography",
            "metrics",
            "segments",
            "assumptions",
            "evidence_slots",
        ):
            object.__setattr__(
                self,
                field_name,
                _string_tuple(getattr(self, field_name), field_name),
            )
        if self.decision_goal is not None:
            if not isinstance(self.decision_goal, str) or not self.decision_goal.strip():
                raise ValueError("decision_goal must be a non-empty string when provided")
            object.__setattr__(self, "decision_goal", self.decision_goal.strip())
        if self.time_scope is not None:
            try:
                json.dumps(self.time_scope, ensure_ascii=False)
            except (TypeError, ValueError) as error:
                raise ValueError("time_scope must be JSON serializable") from error
        if self.freshness_cutoff is not None:
            try:
                date.fromisoformat(self.freshness_cutoff)
            except (TypeError, ValueError) as error:
                raise ValueError("freshness_cutoff must be an ISO date") from error
        for name in (
            "planned_query_budget",
            "domain_tool_budget",
            "research_round_budget",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    @classmethod
    def from_value(cls, value: ResearchContract | Mapping[str, Any]) -> ResearchContract:
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("research contract must be a mapping or ResearchContract")
        allowed = {
            "question",
            "decision_goal",
            "geography",
            "time_scope",
            "metrics",
            "segments",
            "assumptions",
            "evidence_slots",
            "freshness_cutoff",
            "planned_query_budget",
            "domain_tool_budget",
            "research_round_budget",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unknown research contract fields: {', '.join(sorted(unknown))}")
        return cls(**dict(value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "decision_goal": self.decision_goal,
            "geography": list(self.geography),
            "time_scope": self.time_scope,
            "metrics": list(self.metrics),
            "segments": list(self.segments),
            "assumptions": list(self.assumptions),
            "evidence_slots": list(self.evidence_slots),
            "freshness_cutoff": self.freshness_cutoff,
            "planned_query_budget": self.planned_query_budget,
            "domain_tool_budget": self.domain_tool_budget,
            "research_round_budget": self.research_round_budget,
        }
