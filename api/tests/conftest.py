from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_DB = Path(__file__).resolve().parent / "test_ibnussebil.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["GEOCODING_ENABLED"] = "false"
os.environ["ROUTE_GEOMETRY_BASE_URL"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
