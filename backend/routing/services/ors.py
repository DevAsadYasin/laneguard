from __future__ import annotations

import logging
from typing import Any

import httpx
from django.conf import settings

from routing.services.rate_limit import acquire_ors_slot

logger = logging.getLogger(__name__)

LBS_PER_METRIC_TON = 2204.62


class ORSError(Exception):
    pass


def _headers() -> dict[str, str]:
    key = settings.ORS_API_KEY
    if not key:
        raise ORSError(
            "ORS_API_KEY is not configured. Get a free key at https://openrouteservice.org/dev/#/signup"
        )
    return {"Authorization": key, "Content-Type": "application/json"}


def _raise_for_ors(resp: httpx.Response, action: str) -> None:
    if resp.status_code == 429:
        raise ORSError(
            f"{action} rate-limited by OpenRouteService (429). "
            "Wait a minute or lower ORS_RATE_LIMIT_PER_MINUTE / app throttle rates in .env."
        )
    if resp.status_code >= 400:
        raise ORSError(f"{action} failed ({resp.status_code}): {resp.text[:400]}")


def geocode(text: str, *, size: int = 5) -> list[dict[str, Any]]:
    acquire_ors_slot()
    url = f"{settings.ORS_BASE_URL}/geocode/search"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            url,
            headers=_headers(),
            params={"text": text, "size": size},
        )
    _raise_for_ors(resp, "Geocoding")
    data = resp.json()
    results = []
    for feat in data.get("features", []):
        coords = feat.get("geometry", {}).get("coordinates", [])
        props = feat.get("properties", {})
        if len(coords) < 2:
            continue
        results.append(
            {
                "label": props.get("label") or props.get("name") or text,
                "lng": coords[0],
                "lat": coords[1],
            }
        )
    return results


def geocode_one(text: str) -> dict[str, Any]:
    results = geocode(text, size=1)
    if not results:
        raise ORSError(f"No geocoding results for: {text}")
    return results[0]


def truck_gross_weight_tons(load_lbs: float) -> float:
    tare_lbs = float(getattr(settings, "TRUCK_TARE_LBS", 30_000))
    return max(3.5, (float(load_lbs) + tare_lbs) / LBS_PER_METRIC_TON)


def _truck_options(
    *,
    load_lbs: float,
    avoid_features: list[str] | None = None,
) -> dict[str, Any]:
    opts: dict[str, Any] = {
        "vehicle_type": getattr(settings, "TRUCK_VEHICLE_TYPE", "hgv"),
        "profile_params": {
            "restrictions": {
                "length": float(getattr(settings, "TRUCK_LENGTH_M", 16.5)),
                "width": float(getattr(settings, "TRUCK_WIDTH_M", 2.55)),
                "height": float(getattr(settings, "TRUCK_HEIGHT_M", 4.0)),
                "axleload": float(getattr(settings, "TRUCK_AXLELOAD_T", 11.5)),
                "weight": round(truck_gross_weight_tons(load_lbs), 2),
                "hazmat": bool(getattr(settings, "TRUCK_HAZMAT", False)),
            }
        },
    }
    base_avoid = list(avoid_features or [])
    if "ferries" not in base_avoid:
        base_avoid = ["ferries", *base_avoid]
    if base_avoid:
        opts["avoid_features"] = base_avoid
    return opts


def _parse_features(data: dict[str, Any], *, id_start: int = 1) -> list[dict[str, Any]]:
    features = data.get("features") or []
    routes: list[dict[str, Any]] = []
    for idx, feat in enumerate(features):
        geometry = feat.get("geometry", {})
        coords_lnglat = geometry.get("coordinates") or []
        latlng = [(c[1], c[0]) for c in coords_lnglat if len(c) >= 2]
        props = feat.get("properties", {})
        summary = props.get("summary") or {}
        if not summary and props.get("segments"):
            segs = props["segments"]
            summary = {
                "distance": sum(s.get("distance", 0) for s in segs),
                "duration": sum(s.get("duration", 0) for s in segs),
            }
        routes.append(
            {
                "id": f"route-{id_start + idx}",
                "geometry": latlng,
                "distance_meters": float(summary.get("distance") or 0),
                "duration_seconds": float(summary.get("duration") or 0),
                "label": None,
            }
        )
    return routes


def _route_fingerprint(route: dict[str, Any]) -> tuple:
    geom = route.get("geometry") or []
    if not geom:
        return (round(route.get("distance_meters", 0) / 1000), 0, 0)
    mid = geom[len(geom) // 2]
    return (
        round(route.get("distance_meters", 0) / 2000),
        round(mid[0], 2),
        round(mid[1], 2),
    )


def _directions_once(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    profile: str,
    load_lbs: float,
    preference: str | None = None,
    avoid_features: list[str] | None = None,
    alternative_routes: dict[str, Any] | None = None,
    apply_truck_restrictions: bool = True,
) -> list[dict[str, Any]]:
    url = f"{settings.ORS_BASE_URL}/v2/directions/{profile}/geojson"
    body: dict[str, Any] = {
        "coordinates": [[origin[0], origin[1]], [destination[0], destination[1]]],
        "instructions": False,
        "elevation": False,
    }
    if preference:
        body["preference"] = preference
    if alternative_routes:
        body["alternative_routes"] = alternative_routes

    if profile.startswith("driving-hgv") and apply_truck_restrictions:
        body["options"] = _truck_options(load_lbs=load_lbs, avoid_features=avoid_features)
    elif avoid_features:
        body["options"] = {"avoid_features": avoid_features}

    acquire_ors_slot()
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=_headers(), json=body)
    _raise_for_ors(resp, "Directions")
    return _parse_features(resp.json())


def _is_alt_distance_limit(exc: ORSError) -> bool:
    msg = str(exc).lower()
    return "alternative" in msg and ("100000" in msg or "100 km" in msg or "greater than" in msg)


def get_directions(
    origin: tuple[float, float],
    destination: tuple[float, float],
    *,
    load_lbs: float = 40_000,
    profile: str | None = None,
) -> list[dict[str, Any]]:
    profile = profile or getattr(settings, "ORS_ROUTING_PROFILE", "driving-hgv")
    collected: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    strategy = "truck_variants"

    def _add(routes: list[dict[str, Any]], *, label: str | None = None) -> None:
        for r in routes:
            fp = _route_fingerprint(r)
            if fp in seen:
                continue
            seen.add(fp)
            if label and not r.get("label"):
                r["label"] = label
            collected.append(r)

    def _try_profile(active_profile: str) -> None:
        nonlocal strategy
        try:
            alts = _directions_once(
                origin,
                destination,
                profile=active_profile,
                load_lbs=load_lbs,
                alternative_routes={
                    "share_factor": 0.6,
                    "target_count": 2,
                    "weight_factor": 1.6,
                },
            )
            _add(alts, label="hgv_alternative")
            if len(collected) >= 3:
                strategy = "hgv_alternatives"
            elif len(collected) >= 1:
                strategy = "hgv_alternatives_partial"
        except ORSError as exc:
            if _is_alt_distance_limit(exc):
                logger.info(
                    "ORS HGV alternative_routes capped at ~100km; "
                    "using long-haul truck variants"
                )
            else:
                logger.warning("ORS HGV alternatives failed: %s", exc)

        variants: list[tuple[str, dict[str, Any]]] = [
            ("hgv_recommended", {}),
            ("hgv_shortest", {"preference": "shortest"}),
            ("hgv_avoid_tollways", {"avoid_features": ["tollways"]}),
        ]
        for label, opts in variants:
            if len(collected) >= 3:
                break
            try:
                routes = _directions_once(
                    origin,
                    destination,
                    profile=active_profile,
                    load_lbs=load_lbs,
                    **opts,
                )
                _add(routes[:1], label=label)
            except ORSError as exc:
                logger.warning("ORS truck variant '%s' failed: %s", label, exc)

    try:
        _try_profile(profile)
    except ORSError:
        collected.clear()
        seen.clear()
        raise

    if len(collected) < 3 and profile == "driving-hgv":
        logger.warning("HGV yielded %s route(s); falling back to driving-car fill", len(collected))
        try:
            _try_profile("driving-car")
        except ORSError as exc:
            logger.warning("driving-car fallback failed: %s", exc)

    if not collected:
        raise ORSError("Routing API returned no truck routes")

    for i, route in enumerate(collected[:3]):
        route["id"] = f"route-{i + 1}"
        route["strategy"] = strategy if i == 0 else route.get("label") or strategy

    if len(collected) < 3:
        raise ORSError(
            f"Could only build {len(collected)} distinct truck route(s); need 3. "
            "Try another freight lane with more network options."
        )

    return collected[:3]
