from __future__ import annotations

import logging
import math

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Conservative city average when OSRM is not configured.
_FALLBACK_SPEED_MPS = 28_000 / 3600
_TRAFFIC_FACTOR = 1.25


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return int(round(2 * radius * math.asin(math.sqrt(a))))


def _fallback_matrix(points: list[tuple[float, float]]) -> tuple[list[list[int]], list[list[int]]]:
    distances: list[list[int]] = []
    durations: list[list[int]] = []
    for lat1, lon1 in points:
        distance_row: list[int] = []
        duration_row: list[int] = []
        for lat2, lon2 in points:
            meters = haversine_m(lat1, lon1, lat2, lon2)
            distance_row.append(meters)
            seconds = int(round((meters / _FALLBACK_SPEED_MPS) * _TRAFFIC_FACTOR))
            duration_row.append(seconds)
        distances.append(distance_row)
        durations.append(duration_row)
    return distances, durations


def build_matrix(points: list[tuple[float, float]]) -> tuple[list[list[int]], list[list[int]], str]:
    """Return (distance_m, duration_s, source).

    OSRM is optional. Without it, the optimizer still works using a
    deterministic Haversine estimate so the product can run with zero paid
    services.
    """
    if not points:
        return [], [], "empty"
    if not settings.OSRM_BASE_URL:
        distances, durations = _fallback_matrix(points)
        return distances, durations, "haversine"

    coords = ";".join(f"{lon},{lat}" for lat, lon in points)
    url = f"{settings.OSRM_BASE_URL.rstrip('/')}/table/v1/driving/{coords}"
    try:
        with httpx.Client(timeout=settings.OSRM_TIMEOUT_SECONDS) as client:
            response = client.get(url, params={"annotations": "distance,duration"})
            response.raise_for_status()
            payload = response.json()
            distances = payload.get("distances")
            durations = payload.get("durations")
            if distances and durations and len(distances) == len(points):
                return (
                    [[int(value or 0) for value in row] for row in distances],
                    [[int(value or 0) for value in row] for row in durations],
                    "osrm",
                )
    except Exception:
        logger.warning("OSRM matrix failed, using Haversine fallback", exc_info=True)

    distances, durations = _fallback_matrix(points)
    return distances, durations, "haversine"
