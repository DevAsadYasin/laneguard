import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from routing.services.rate_limit import RateLimitExceeded, SlidingWindowLimiter


def test_sliding_window_blocks_after_max():
    limiter = SlidingWindowLimiter(max_calls=3, window_seconds=60.0)
    limiter.acquire()
    limiter.acquire()
    limiter.acquire()
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.acquire()
    assert exc.value.retry_after >= 1


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "UNAUTHENTICATED_USER": None,
        "DEFAULT_THROTTLE_CLASSES": ["routing.throttles.EnvScopedRateThrottle"],
        "DEFAULT_THROTTLE_RATES": {
            "geocode": "2/min",
            "analyze": "6/min",
            "default": "60/min",
        },
        "EXCEPTION_HANDLER": "routing.exceptions.custom_exception_handler",
    }
)
def test_geocode_throttle_returns_429(monkeypatch):
    cache.clear()
    client = APIClient()

    monkeypatch.setattr(
        "routing.views.autocomplete",
        lambda q: [{"label": q, "lat": 1.0, "lng": 2.0}],
    )

    url = reverse("geocode")
    assert client.get(url, {"q": "Chi"}).status_code == 200
    assert client.get(url, {"q": "Chic"}).status_code == 200
    resp = client.get(url, {"q": "Chicago"})
    assert resp.status_code == 429
    assert "retry_after" in resp.json()
