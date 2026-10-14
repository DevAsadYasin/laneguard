from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from django.conf import settings


class WeatherError(Exception):
    pass


KMH_TO_MPH = 0.621371
MM_TO_IN = 1 / 25.4
CM_TO_IN = 1 / 2.54


def _parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def fetch_hourly_forecast(
    lat: float,
    lon: float,
    *,
    forecast_days: int | None = None,
) -> dict[str, Any]:
    days = forecast_days
    if days is None:
        days = int(getattr(settings, "WEATHER_FORECAST_DAYS", 8))
    days = max(1, min(int(days), 16))

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,precipitation,snowfall",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "UTC",
        "forecast_days": days,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(settings.OPEN_METEO_URL, params=params)
    if resp.status_code >= 400:
        raise WeatherError(f"Open-Meteo error ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    hourly = data.get("hourly") or {}
    times_raw = hourly.get("time") or []
    wind = hourly.get("wind_speed_10m") or []
    precip = hourly.get("precipitation") or []
    snow = hourly.get("snowfall") or []

    times = [_parse_iso(t) for t in times_raw]
    wind_mph = [(w or 0) * KMH_TO_MPH for w in wind]
    rain_in_hr = [(p or 0) * MM_TO_IN for p in precip]
    snow_in_hr = [(s or 0) * CM_TO_IN for s in snow]

    return {
        "times": times,
        "wind_mph": wind_mph,
        "rain_in_hr": rain_in_hr,
        "snow_in_hr": snow_in_hr,
        "forecast_days": days,
    }


def weather_at_eta(forecast: dict[str, Any], eta: datetime) -> dict[str, Any]:
    times: list[datetime] = forecast["times"]
    if not times:
        return {
            "wind_mph": 0.0,
            "rain_in_hr": 0.0,
            "snow_in_hr": 0.0,
            "forecast_unavailable": True,
            "matched_time": None,
        }

    if eta.tzinfo is None:
        eta = eta.replace(tzinfo=timezone.utc)

    best_i = 0
    best_delta = abs((times[0] - eta).total_seconds())
    for i, t in enumerate(times):
        delta = abs((t - eta).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best_i = i

    unavailable = best_delta > 5400
    return {
        "wind_mph": round(forecast["wind_mph"][best_i], 2) if not unavailable else 0.0,
        "rain_in_hr": round(forecast["rain_in_hr"][best_i], 4) if not unavailable else 0.0,
        "snow_in_hr": round(forecast["snow_in_hr"][best_i], 4) if not unavailable else 0.0,
        "forecast_unavailable": unavailable,
        "matched_time": times[best_i].isoformat() if not unavailable else None,
    }
