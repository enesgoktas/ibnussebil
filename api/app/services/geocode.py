from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[float, float] | None] = {}


def geocode_address(address: str) -> tuple[float, float] | None:
    query = address.strip()
    if not query:
        return None
    if query.lower() in _cache:
        return _cache[query.lower()]

    if not settings.GEOCODING_ENABLED:
        return None

    if "türkiye" not in query.lower() and "turkey" not in query.lower():
        query = f"{query}, Türkiye"

    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(
                settings.GEOCODER_URL,
                params={"q": query, "limit": 1, "lang": "tr"},
                headers={"User-Agent": "Ibnussebil/1.0 (dispatch demo)"},
            )
            response.raise_for_status()
            features = response.json().get("features") or []
            if not features:
                _cache[address.strip().lower()] = None
                return None
            lon, lat = features[0]["geometry"]["coordinates"]
            result = (float(lat), float(lon))
            _cache[address.strip().lower()] = result
            return result
    except Exception:
        logger.warning("Geocoding failed for %r", address, exc_info=True)
        return None
