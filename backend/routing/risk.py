from __future__ import annotations

from enum import IntEnum
from typing import Iterable


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }[self]


def classify_wind(mph: float) -> RiskLevel:
    if mph < 25:
        return RiskLevel.LOW
    if mph < 35:
        return RiskLevel.MODERATE
    if mph < 45:
        return RiskLevel.HIGH
    if mph < 55:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_rain(inches_per_hour: float) -> RiskLevel:
    if inches_per_hour < 0.10:
        return RiskLevel.LOW
    if inches_per_hour < 0.25:
        return RiskLevel.MODERATE
    if inches_per_hour < 0.50:
        return RiskLevel.HIGH
    if inches_per_hour <= 1.00:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_snow(inches_per_hour: float) -> RiskLevel:
    if inches_per_hour < 0.5:
        return RiskLevel.LOW
    if inches_per_hour < 1.0:
        return RiskLevel.MODERATE
    if inches_per_hour < 2.0:
        return RiskLevel.HIGH
    if inches_per_hour <= 3.0:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def apply_load_rules(wind_mph: float, load_lbs: float, wind_level: RiskLevel) -> RiskLevel:
    level = wind_level
    if wind_mph >= 55:
        return RiskLevel.NO_TRAVEL
    if 45 <= wind_mph < 55 and load_lbs > 30_000:
        level = max(level, RiskLevel.NO_TRAVEL)
    if 35 <= wind_mph < 45 and load_lbs > 40_000:
        level = max(level, RiskLevel.SEVERE)
    return level


def checkpoint_risk(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_lbs: float,
) -> dict:
    wind_level = classify_wind(wind_mph)
    rain_level = classify_rain(rain_in_hr)
    snow_level = classify_snow(snow_in_hr)
    wind_with_load = apply_load_rules(wind_mph, load_lbs, wind_level)
    final = max(wind_with_load, rain_level, snow_level)
    return {
        "level": final.label,
        "score": int(final),
        "components": {
            "wind": wind_level.label,
            "rain": rain_level.label,
            "snow": snow_level.label,
            "wind_with_load": wind_with_load.label,
        },
    }


def sample_interval_miles(total_miles: float) -> int:
    if total_miles < 150:
        return 10
    if total_miles <= 400:
        return 25
    return 50


def aggregate_route_risk(
    checkpoint_scores: Iterable[int],
    checkpoint_miles: Iterable[float],
    travel_time_seconds: float,
) -> dict:
    scores = list(checkpoint_scores)
    miles = list(checkpoint_miles)
    if len(scores) != len(miles):
        raise ValueError("checkpoint scores and miles length mismatch")
    if len(scores) == 0:
        return {
            "no_travel_miles": 0.0,
            "severe_miles": 0.0,
            "high_miles": 0.0,
            "avg_risk": 0.0,
            "travel_time_seconds": travel_time_seconds,
        }

    no_travel = severe = high = 0.0
    weighted_sum = 0.0
    total_seg = 0.0

    if len(scores) == 1:
        return {
            "no_travel_miles": 0.0,
            "severe_miles": 0.0,
            "high_miles": 0.0,
            "avg_risk": float(scores[0]),
            "travel_time_seconds": travel_time_seconds,
        }

    for i in range(len(scores) - 1):
        seg_miles = max(0.0, miles[i + 1] - miles[i])
        seg_score = max(scores[i], scores[i + 1])
        total_seg += seg_miles
        weighted_sum += seg_score * seg_miles
        if seg_score == RiskLevel.NO_TRAVEL:
            no_travel += seg_miles
        elif seg_score == RiskLevel.SEVERE:
            severe += seg_miles
        elif seg_score == RiskLevel.HIGH:
            high += seg_miles

    avg_risk = (weighted_sum / total_seg) if total_seg > 0 else float(max(scores))
    return {
        "no_travel_miles": round(no_travel, 3),
        "severe_miles": round(severe, 3),
        "high_miles": round(high, 3),
        "avg_risk": round(avg_risk, 4),
        "travel_time_seconds": travel_time_seconds,
    }


def recommend_route(route_summaries: list[dict]) -> str:
    if not route_summaries:
        raise ValueError("no routes to recommend")
    ranked = sorted(
        route_summaries,
        key=lambda r: (
            r["no_travel_miles"],
            r["severe_miles"],
            r["high_miles"],
            r["avg_risk"],
            r["travel_time_seconds"],
        ),
    )
    return ranked[0]["id"]
