from __future__ import annotations

import math
from typing import Sequence

METERS_PER_MILE = 1609.344


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def cumulative_distances_meters(coords: Sequence[tuple[float, float]]) -> list[float]:
    if not coords:
        return []
    cum = [0.0]
    for i in range(1, len(coords)):
        d = haversine_meters(coords[i - 1][0], coords[i - 1][1], coords[i][0], coords[i][1])
        cum.append(cum[-1] + d)
    return cum


def point_at_distance(
    coords: Sequence[tuple[float, float]],
    cum_m: Sequence[float],
    target_m: float,
) -> tuple[float, float, float]:
    if not coords:
        raise ValueError("empty coords")
    total = cum_m[-1]
    if target_m <= 0:
        return coords[0][0], coords[0][1], 0.0
    if target_m >= total:
        return coords[-1][0], coords[-1][1], total

    for i in range(1, len(cum_m)):
        if cum_m[i] >= target_m:
            seg_start = cum_m[i - 1]
            seg_len = cum_m[i] - seg_start
            t = 0.0 if seg_len == 0 else (target_m - seg_start) / seg_len
            lat = coords[i - 1][0] + t * (coords[i][0] - coords[i - 1][0])
            lon = coords[i - 1][1] + t * (coords[i][1] - coords[i - 1][1])
            return lat, lon, target_m
    return coords[-1][0], coords[-1][1], total


def sample_checkpoints(
    coords: Sequence[tuple[float, float]],
    interval_miles: float,
    total_duration_seconds: float,
) -> list[dict]:
    if len(coords) < 2:
        lat, lon = coords[0] if coords else (0.0, 0.0)
        return [
            {
                "lat": lat,
                "lng": lon,
                "mile": 0.0,
                "eta_offset_seconds": 0.0,
            }
        ]

    cum = cumulative_distances_meters(coords)
    total_m = cum[-1]
    total_miles = total_m / METERS_PER_MILE

    checkpoints: list[dict] = []
    mile = 0.0
    while mile < total_miles - 1e-6:
        target_m = mile * METERS_PER_MILE
        lat, lon, actual_m = point_at_distance(coords, cum, target_m)
        frac = 0.0 if total_m == 0 else actual_m / total_m
        checkpoints.append(
            {
                "lat": lat,
                "lng": lon,
                "mile": round(actual_m / METERS_PER_MILE, 3),
                "eta_offset_seconds": frac * total_duration_seconds,
            }
        )
        mile += interval_miles

    checkpoints.append(
        {
            "lat": coords[-1][0],
            "lng": coords[-1][1],
            "mile": round(total_miles, 3),
            "eta_offset_seconds": total_duration_seconds,
        }
    )

    if len(checkpoints) >= 2 and abs(checkpoints[-1]["mile"] - checkpoints[-2]["mile"]) < 0.05:
        checkpoints.pop(-2)

    return checkpoints


def densify_corridor(
    routes_coords: Sequence[Sequence[tuple[float, float]]],
    step_miles: float = 15.0,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for coords in routes_coords:
        if len(coords) < 2:
            continue
        cum = cumulative_distances_meters(coords)
        total_m = cum[-1]
        step_m = step_miles * METERS_PER_MILE
        d = 0.0
        while d <= total_m:
            lat, lon, _ = point_at_distance(coords, cum, d)
            key = (round(lat, 3), round(lon, 3))
            if key not in seen:
                seen.add(key)
                points.append((lat, lon))
            d += step_m
    return points
