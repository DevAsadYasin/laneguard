from datetime import datetime, timedelta, timezone

from django.urls import reverse
from rest_framework.test import APIClient


def test_reject_past_departure():
    client = APIClient()
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    resp = client.post(
        reverse("analyze"),
        {
            "origin": "Chicago, IL",
            "destination": "Detroit, MI",
            "departure_at": past,
            "load_lbs": 20000,
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "past" in str(resp.data).lower()


def test_reject_too_far_future_departure():
    client = APIClient()
    far = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    resp = client.post(
        reverse("analyze"),
        {
            "origin": "Chicago, IL",
            "destination": "Detroit, MI",
            "departure_at": far,
            "load_lbs": 20000,
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "within" in str(resp.data).lower() or "forecast" in str(resp.data).lower()


def test_accept_departure_within_seven_days():
    client = APIClient()
    soon = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    resp = client.post(
        reverse("analyze"),
        {
            "origin": {"lat": 41.88, "lng": -87.63, "label": "Chicago"},
            "destination": {"lat": 42.33, "lng": -83.05, "label": "Detroit"},
            "departure_at": soon,
            "load_lbs": 20000,
        },
        format="json",
    )
    assert resp.status_code != 400 or "departure_at" not in resp.data

