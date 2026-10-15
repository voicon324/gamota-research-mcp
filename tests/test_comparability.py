from __future__ import annotations

from gamota_research.comparability import compare_evidence


def _evidence(**overrides):
    fields = {
        "metric": "revenue_growth",
        "unit": "%",
        "market": "VN",
        "period_start": "2025-01-01",
        "period_end": "2025-06-30",
        "scope": None,
        "metadata": {},
    }
    fields.update(overrides)
    return fields


def test_same_metric_unit_market_period_and_optional_scope_are_comparable():
    result = compare_evidence(
        _evidence(metadata={"platform": "Android", "store": "Google Play"}),
        _evidence(metadata={"platform": "android", "store": "google play"}),
    )

    assert result.comparable is True
    assert result.reasons == ()
    assert result.signature["metric"] == "revenue_growth"


def test_downloads_and_revenue_are_not_comparable():
    result = compare_evidence(
        _evidence(metric="downloads_growth"),
        _evidence(metric="revenue_growth"),
    )

    assert result.comparable is False
    assert "metric_mismatch" in result.reasons


def test_vietnam_and_southeast_asia_are_not_comparable():
    result = compare_evidence(
        _evidence(market="VN"),
        _evidence(market="SEA"),
    )

    assert result.comparable is False
    assert "market_mismatch" in result.reasons


def test_different_periods_are_not_comparable():
    result = compare_evidence(
        _evidence(period_start="2025-01-01", period_end="2025-03-31"),
        _evidence(period_start="2025-04-01", period_end="2025-06-30"),
    )

    assert result.comparable is False
    assert "period_start_mismatch" in result.reasons
    assert "period_end_mismatch" in result.reasons


def test_missing_critical_dimension_is_not_assumed_comparable():
    result = compare_evidence(
        _evidence(),
        _evidence(period_end=None),
    )

    assert result.comparable is False
    assert "missing_period_end" in result.reasons


def test_declared_sample_scope_must_match():
    result = compare_evidence(
        _evidence(metadata={"sample_scope": "top 100 games"}),
        _evidence(metadata={"sample_scope": "all games"}),
    )

    assert result.comparable is False
    assert "sample_scope_mismatch" in result.reasons
