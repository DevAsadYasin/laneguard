from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from django.conf import settings as dj_settings

from routing.geometry import METERS_PER_MILE, densify_corridor, sample_checkpoints
from routing.risk import (
    aggregate_route_risk,
    checkpoint_risk,
    recommend_route,
    sample_interval_miles,
)
from routing.services import open_meteo, ors


def _parse_departure(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        raw = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _resolve_point(value: str | dict) -> dict[str, Any]:
    if isinstance(value, dict) and "lat" in value and "lng" in value:
        return {
            "label": value.get("label") or f"{value['lat']},{value['lng']}",
            "lat": float(value["lat"]),
            "lng": float(value["lng"]),
        }
    text = value if isinstance(value, str) else str(value)
    return ors.geocode_one(text)


def _fetch_forecast_cached(
    cache: dict[tuple[float, float], dict],
    lat: float,
    lon: float,
) -> dict:
    key = (round(lat, 2), round(lon, 2))
    if key not in cache:
        cache[key] = open_meteo.fetch_hourly_forecast(lat, lon)
    return cache[key]


def analyze_trip(
    *,
    origin: str | dict,
    destination: str | dict,
    departure_at: str | datetime,
    load_lbs: float,
) -> dict[str, Any]:
    origin_pt = _resolve_point(origin)
    dest_pt = _resolve_point(destination)
    departure = _parse_departure(departure_at)

    profile_used = "driving-hgv"
    raw_routes = ors.get_directions(
        (origin_pt["lng"], origin_pt["lat"]),
        (dest_pt["lng"], dest_pt["lat"]),
        load_lbs=load_lbs,
        profile="driving-hgv",
    )

    if not raw_routes:
        raise ors.ORSError("Routing API returned no routes")

    routes_out: list[dict[str, Any]] = []
    forecast_cache: dict[tuple[float, float], dict] = {}

    primary_miles = raw_routes[0]["distance_meters"] / METERS_PER_MILE
    interval = sample_interval_miles(primary_miles)

    for route in raw_routes[:3]:
        coords = route["geometry"]
        duration = route["duration_seconds"]
        distance_m = route["distance_meters"]
        distance_miles = distance_m / METERS_PER_MILE
        route_interval = sample_interval_miles(distance_miles)

        cps = sample_checkpoints(coords, route_interval, duration)
        enriched = []
        scores = []
        miles = []

        for cp in cps:
            eta = departure + timedelta(seconds=cp["eta_offset_seconds"])
            forecast = _fetch_forecast_cached(forecast_cache, cp["lat"], cp["lng"])
            wx = open_meteo.weather_at_eta(forecast, eta)
            if wx["forecast_unavailable"]:
                risk = {
                    "level": "Moderate",
                    "score": 1,
                    "components": {
                        "wind": "Moderate",
                        "rain": "Moderate",
                        "snow": "Moderate",
                        "wind_with_load": "Moderate",
                    },
                    "warning": "forecast_unavailable",
                }
            else:
                risk = checkpoint_risk(
                    wx["wind_mph"],
                    wx["rain_in_hr"],
                    wx["snow_in_hr"],
                    load_lbs,
                )
            enriched.append(
                {
                    **cp,
                    "eta": eta.isoformat(),
                    "weather": {
                        "wind_mph": wx["wind_mph"],
                        "rain_in_hr": wx["rain_in_hr"],
                        "snow_in_hr": wx["snow_in_hr"],
                        "matched_time": wx["matched_time"],
                        "forecast_unavailable": wx["forecast_unavailable"],
                    },
                    "risk": risk,
                }
            )
            scores.append(risk["score"])
            miles.append(cp["mile"])

        summary = aggregate_route_risk(scores, miles, duration)
        summary.update(
            {
                "id": route["id"],
                "distance_miles": round(distance_miles, 2),
                "distance_meters": distance_m,
                "sample_interval_miles": route_interval,
                "label": route.get("label") or route["id"],
            }
        )
        routes_out.append(
            {
                "id": route["id"],
                "label": route.get("label") or route["id"],
                "geometry": [{"lat": lat, "lng": lng} for lat, lng in coords],
                "checkpoints": enriched,
                "summary": summary,
            }
        )

    if len(routes_out) < 3:
        raise ors.ORSError(
            f"Could only build {len(routes_out)} distinct route(s); need 3. "
            "Try another city pair with more road-network options."
        )

    summaries = [r["summary"] for r in routes_out]
    recommended_id = recommend_route(summaries)

    heatmap_hours = int(getattr(dj_settings, "HEATMAP_HOURS", 48))
    heatmap_base = departure
    corridor = densify_corridor(
        [[(p["lat"], p["lng"]) for p in r["geometry"]] for r in routes_out],
        step_miles=20.0,
    )
    if len(corridor) > 40:
        step = max(1, len(corridor) // 40)
        corridor = corridor[::step][:40]

    for lat, lon in corridor:
        _fetch_forecast_cached(forecast_cache, lat, lon)

    heatmap_by_hour: list[list[dict[str, float]]] = [[] for _ in range(heatmap_hours + 1)]
    for lat, lon in corridor:
        fc = _fetch_forecast_cached(forecast_cache, lat, lon)
        for hour in range(heatmap_hours + 1):
            target = heatmap_base + timedelta(hours=hour)
            wx = open_meteo.weather_at_eta(fc, target)
            if wx["forecast_unavailable"]:
                intensity = 0.0
            else:
                intensity = min(
                    1.0,
                    max(
                        wx["wind_mph"] / 55.0,
                        wx["rain_in_hr"] / 1.0,
                        wx["snow_in_hr"] / 3.0,
                    ),
                )
            heatmap_by_hour[hour].append(
                {
                    "lat": lat,
                    "lng": lon,
                    "intensity": round(intensity, 3),
                }
            )

    return {
        "origin": origin_pt,
        "destination": dest_pt,
        "departure_at": departure.isoformat(),
        "load_lbs": load_lbs,
        "sample_interval_miles": interval,
        "routing_profile": profile_used,
        "routes": routes_out,
        "recommended_route_id": recommended_id,
        "recommendation_order": [
            "fewest_no_travel_miles",
            "fewest_severe_miles",
            "fewest_high_miles",
            "lowest_avg_risk",
            "shortest_travel_time",
        ],
        "heatmap_by_hour": heatmap_by_hour,
        "heatmap_hours": heatmap_hours,
        "departure_max_hours_ahead": int(dj_settings.DEPARTURE_MAX_HOURS_AHEAD),
        "weather_forecast_days": int(dj_settings.WEATHER_FORECAST_DAYS),
    }


def autocomplete(query: str) -> list[dict[str, Any]]:
    if not query or len(query.strip()) < 2:
        return []
    return ors.geocode(query.strip(), size=5)
