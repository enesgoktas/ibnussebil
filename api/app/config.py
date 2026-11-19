from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ibnussebil"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./ibnussebil.db"
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:4173,http://127.0.0.1:4173"
    )

    # Optional. If empty, v1 falls back to a haversine estimate.
    OSRM_BASE_URL: str = ""
    OSRM_TIMEOUT_SECONDS: float = 8.0

    # Road-following map geometry. If OSRM_BASE_URL is set it is used first;
    # otherwise this public demo server keeps the map honest for v1.
    # Set ROUTE_GEOMETRY_BASE_URL="" to disable and use straight fallback lines.
    ROUTE_GEOMETRY_BASE_URL: str = "https://router.project-osrm.org"
    ROUTE_GEOMETRY_TIMEOUT_SECONDS: float = 10.0

    # Public Photon instance by default. No API key is required.
    GEOCODING_ENABLED: bool = True
    GEOCODER_URL: str = "https://photon.komoot.io/api"

    OPTIMIZER_TIME_LIMIT_SECONDS: int = 5
    MAX_IMPORT_ROWS: int = 1000
    MAX_GEOCODE_ROWS_PER_IMPORT: int = 100

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.CORS_ORIGINS.split(",") if value.strip()]


settings = Settings()
