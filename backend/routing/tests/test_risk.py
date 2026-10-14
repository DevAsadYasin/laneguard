import pytest

from routing.risk import (
    RiskLevel,
    aggregate_route_risk,
    checkpoint_risk,
    classify_rain,
    classify_snow,
    classify_wind,
    recommend_route,
    sample_interval_miles,
)


@pytest.mark.parametrize(
    "mph,expected",
    [
        (0, RiskLevel.LOW),
        (24.9, RiskLevel.LOW),
        (25, RiskLevel.MODERATE),
        (34, RiskLevel.MODERATE),
        (35, RiskLevel.HIGH),
        (44, RiskLevel.HIGH),
        (45, RiskLevel.SEVERE),
        (54, RiskLevel.SEVERE),
        (55, RiskLevel.NO_TRAVEL),
        (80, RiskLevel.NO_TRAVEL),
    ],
)
def test_classify_wind_boundaries(mph, expected):
    assert classify_wind(mph) == expected


@pytest.mark.parametrize(
    "rate,expected",
    [
        (0.0, RiskLevel.LOW),
        (0.099, RiskLevel.LOW),
        (0.10, RiskLevel.MODERATE),
        (0.249, RiskLevel.MODERATE),
        (0.25, RiskLevel.HIGH),
        (0.499, RiskLevel.HIGH),
        (0.50, RiskLevel.SEVERE),
        (1.00, RiskLevel.SEVERE),
        (1.01, RiskLevel.NO_TRAVEL),
    ],
)
def test_classify_rain_boundaries(rate, expected):
    assert classify_rain(rate) == expected


@pytest.mark.parametrize(
    "rate,expected",
    [
        (0.0, RiskLevel.LOW),
        (0.49, RiskLevel.LOW),
        (0.5, RiskLevel.MODERATE),
        (0.99, RiskLevel.MODERATE),
        (1.0, RiskLevel.HIGH),
        (1.99, RiskLevel.HIGH),
        (2.0, RiskLevel.SEVERE),
        (3.0, RiskLevel.SEVERE),
        (3.01, RiskLevel.NO_TRAVEL),
    ],
)
def test_classify_snow_boundaries(rate, expected):
    assert classify_snow(rate) == expected


def test_load_rule_55_any_load():
    result = checkpoint_risk(55, 0, 0, 1000)
    assert result["level"] == "No Travel"


def test_load_rule_45_54_heavy():
    light = checkpoint_risk(50, 0, 0, 30_000)
    heavy = checkpoint_risk(50, 0, 0, 30_001)
    assert light["level"] == "Severe"
    assert heavy["level"] == "No Travel"


def test_load_rule_35_44_heavy():
    light = checkpoint_risk(40, 0, 0, 40_000)
    heavy = checkpoint_risk(40, 0, 0, 40_001)
    assert light["level"] == "High"
    assert heavy["level"] == "Severe"


def test_rain_no_travel_beats_wind():
    result = checkpoint_risk(10, 1.5, 0, 5000)
    assert result["level"] == "No Travel"


def test_sample_interval_adaptive():
    assert sample_interval_miles(100) == 10
    assert sample_interval_miles(149.9) == 10
    assert sample_interval_miles(150) == 25
    assert sample_interval_miles(400) == 25
    assert sample_interval_miles(400.1) == 50


def test_aggregate_and_recommend_order():
    a = aggregate_route_risk([0, 2, 2], [0, 10, 20], 3600)
    b = aggregate_route_risk([0, 3, 3], [0, 10, 20], 3000)
    assert a["high_miles"] == 20
    assert b["severe_miles"] == 20
    recommended = recommend_route(
        [
            {"id": "a", **a},
            {"id": "b", **b},
        ]
    )
    assert recommended == "a"


def test_recommend_no_travel_first():
    safe = {
        "id": "safe",
        "no_travel_miles": 0,
        "severe_miles": 50,
        "high_miles": 0,
        "avg_risk": 3,
        "travel_time_seconds": 99999,
    }
    bad = {
        "id": "bad",
        "no_travel_miles": 1,
        "severe_miles": 0,
        "high_miles": 0,
        "avg_risk": 0,
        "travel_time_seconds": 100,
    }
    assert recommend_route([safe, bad]) == "safe"


def test_recommend_tie_break_time():
    a = {
        "id": "slow",
        "no_travel_miles": 0,
        "severe_miles": 0,
        "high_miles": 0,
        "avg_risk": 1,
        "travel_time_seconds": 5000,
    }
    b = {
        "id": "fast",
        "no_travel_miles": 0,
        "severe_miles": 0,
        "high_miles": 0,
        "avg_risk": 1,
        "travel_time_seconds": 4000,
    }
    assert recommend_route([a, b]) == "fast"
