from unittest.mock import patch

import pytest

from routing.services.ors import ORSError, get_directions, truck_gross_weight_tons


def _route(distance_m: float, mid_lat: float, mid_lng: float) -> dict:
    return {
        "id": "route-x",
        "geometry": [
            (41.0, -87.0),
            (mid_lat, mid_lng),
            (42.0, -83.0),
        ],
        "distance_meters": distance_m,
        "duration_seconds": 10_000,
        "label": None,
    }


def test_truck_gross_weight_includes_tare():
    assert 30 < truck_gross_weight_tons(40_000) < 35


def test_get_directions_uses_hgv_variants_when_alts_blocked():
    profiles: list[str] = []

    def fake_once(*args, **kwargs):
        profiles.append(kwargs.get("profile"))
        if kwargs.get("alternative_routes"):
            raise ORSError(
                "Directions failed (400): approximated route distance must not be "
                "greater than 100000.0 meters for use with the alternative Routes"
            )
        pref = kwargs.get("preference")
        avoid = kwargs.get("avoid_features") or []
        assert "load_lbs" in kwargs
        if pref == "shortest":
            return [_route(400_000, 41.5, -85.0)]
        if "tollways" in avoid:
            return [_route(460_000, 42.2, -85.5)]
        return [_route(450_000, 42.0, -85.2)]

    with patch("routing.services.ors._directions_once", side_effect=fake_once):
        routes = get_directions(
            (-87.6, 41.8),
            (-83.0, 42.3),
            load_lbs=40_000,
            profile="driving-hgv",
        )

    assert len(routes) == 3
    assert all(p == "driving-hgv" for p in profiles if p)
    assert {r["label"] for r in routes} >= {
        "hgv_recommended",
        "hgv_shortest",
        "hgv_avoid_tollways",
    }


def test_get_directions_prefers_native_hgv_alts_when_available():
    alts = [
        _route(50_000, 49.41, 8.68),
        _route(52_000, 49.42, 8.70),
        _route(55_000, 49.43, 8.72),
    ]

    with patch("routing.services.ors._directions_once", return_value=alts) as mock_once:
        routes = get_directions(
            (8.68, 49.41),
            (8.78, 49.42),
            load_lbs=35_000,
            profile="driving-hgv",
        )

    assert len(routes) == 3
    assert mock_once.call_count == 1
    assert mock_once.call_args.kwargs["profile"] == "driving-hgv"
