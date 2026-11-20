from typing import Generator


import pytest
from fastapi.testclient import TestClient

from app.main import app

# Cliente de prueba
@pytest.fixture(scope="module")
def client() -> Generator:
    with TestClient(app) as _client:
        yield _client
        app.dependency_overrides = {}
