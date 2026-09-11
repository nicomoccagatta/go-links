from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from golinks_api.main import create_app
from golinks_api.settings import Settings


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'golinks.db'}",
        go_base_url="http://localhost:8000",
        frontend_url="http://localhost:5173",
    )
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, follow_redirects=False) as client:
        yield client
