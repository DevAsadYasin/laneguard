from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api():
    return APIClient()


def _fake_routes():
    return [
        {
            "id": "route-1",
            "geometry": [(41.88, -87.63), (41.9, -87.0), (42.3, -83.0)],
            "distance_meters": 400_000,
            "duration_seconds": 14_400,
        },
        {
            "id": "route-2",
            "geometry": [(41.88, -87.63), (41.5, -86.5), (42.3, -83.0)],
            "distance_meters": 420_000,
            "duration_seconds": 15_000,
        },
        {
            "id": "route-3",
            "geometry": [(41.88, -87.63), (42.2, -86.0), (42.3, -83.0)],
            "distance_meters": 410_000,
            "duration_seconds": 14_800,
        },
    ]


def _fake_forecast(base: datetime | None = None):
    base = base or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = [base + timedelta(hours=i) for i in range(49)]
    return {
        "times": times,
        "wind_mph": [10.0] * 49,
        "rain_in_hr": [0.0] * 49,
        "snow_in_hr": [0.0] * 49,
    }


@patch("routing.services.analyze.ors.get_directions", return_value=_fake_routes())
@patch(
    "routing.services.analyze.ors.geocode_one",
    side_effect=[
        {"label": "Chicago, IL", "lat": 41.88, "lng": -87.63},
        {"label": "Detroit, MI", "lat": 42.33, "lng": -83.05},
    ],
)
@patch(
    "routing.services.analyze.open_meteo.fetch_hourly_forecast",
    side_effect=lambda *a, **k: _fake_forecast(),
)
def test_analyze_happy_path(mock_wx, mock_geo, mock_dir, api):
    url = reverse("analyze")
    departure = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    payload = {
        "origin": "Chicago, IL",
        "destination": "Detroit, MI",
        "departure_at": departure,
        "load_lbs": 20000,
    }
    resp = api.post(url, payload, format="json")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert len(data["routes"]) == 3
    assert data["recommended_route_id"] in {r["id"] for r in data["routes"]}
    assert data["sample_interval_miles"] in (10, 25, 50)
    assert len(data["heatmap_by_hour"]) == data["heatmap_hours"] + 1
    assert data["routes"][0]["checkpoints"]
    assert "risk" in data["routes"][0]["checkpoints"][0]
