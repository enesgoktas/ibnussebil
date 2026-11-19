from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_GEOMETRY_CACHE_MAX = 128
_cache: dict[tuple[tuple[float, float], ...], "GeometryResult"] = {}


@dataclass(frozen=True)
class GeometryResult:
    coordinates: list[tuple[float, float]]
    source: str


def _fallback(points: list[tuple[float, float]]) -> GeometryResult:
    return GeometryResult(coordinates=points, source="fallback")


def route_geometry(points: list[tuple[float, float]]) -> GeometryResult:
    """Return road-following coordinates for a sequence of (lat, lon) points.

    OSRM is optional. If it is unreachable or not configured, the caller gets
    the straight-line fallback so the map still renders.
    """
    if len(points) < 2:
        return _fallback(points)

    key = tuple((round(lat, 5), round(lon, 5)) for lat, lon in points)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    base_url = (settings.OSRM_BASE_URL or settings.ROUTE_GEOMETRY_BASE_URL).rstrip("/")
    if not base_url:
        return _fallback(points)

    coords_path = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)
    url = f"{base_url}/route/v1/driving/{coords_path}"
    try:
        with httpx.Client(timeout=settings.ROUTE_GEOMETRY_TIMEOUT_SECONDS) as client:
            response = client.get(
                url,
                params={"overview": "full", "geometries": "geojson", "steps": "false"},
                headers={"User-Agent": "Ibnussebil/1.0 (dispatch demo)"},
            )
            response.raise_for_status()
            payload = response.json()
            routes = payload.get("routes") or []
            if not routes:
                return _fallback(points)
            raw = routes[0].get("geometry", {}).get("coordinates") or []
            coordinates = [(float(lat), float(lon)) for lon, lat in raw]
            if len(coordinates) < 2:
                return _fallback(points)
            result = GeometryResult(coordinates=coordinates, source="osrm")
            if len(_cache) >= _GEOMETRY_CACHE_MAX:
                _cache.clear()
            _cache[key] = result
            return result
    except Exception:
        logger.warning("Route geometry failed, using straight fallback", exc_info=True)
        return _fallback(points)
