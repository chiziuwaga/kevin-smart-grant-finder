from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app and services mapping
test_app = __import__('Home').main_app
services = __import__('Home').services

client = TestClient(test_app)

class DummySession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, query):
        return None


class FailingSession(DummySession):
    async def execute(self, query):
        raise Exception("Connection failed")


def test_health_success(monkeypatch):
    # Simulate successful DB ping
    monkeypatch.setattr(services, 'db_sessionmaker', lambda: DummySession())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "detail": "Database connected"}


def test_health_failure(monkeypatch):
    # Simulate DB ping failure
    monkeypatch.setattr(services, 'db_sessionmaker', lambda: FailingSession())
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data.get("status") == "error"
    assert "Connection failed" in data.get("detail", "")
