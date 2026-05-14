import os
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://hitalent:hitalent@127.0.0.1:5432/hitalent",
)

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def engine():
    url = os.environ["DATABASE_URL"]
    eng = create_engine(url)
    cfg = AlembicConfig(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    return eng


@pytest.fixture(autouse=True)
def _clean_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE departments RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
