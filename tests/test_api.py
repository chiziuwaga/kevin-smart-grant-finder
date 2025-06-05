from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app and services mapping
test_app = __import__('Home').main_app
services = __import__('Home').services

client = TestClient(test_app)

class DummySession:
    def __init__(self, fail=False):
        self.fail = fail

    async def __aenter__(self):
        if self.fail:
            raise Exception("Connection failed")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, query):
        if self.fail:
            raise Exception("Connection failed")
        return {}

class DummySessionMaker:
    def __init__(self, fail=False):
        self.fail = fail
    def __call__(self):
        return DummySession(self.fail)


def test_health_success(monkeypatch):
    monkeypatch.setattr(services, 'db_sessionmaker', DummySessionMaker(fail=False))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "detail": "Database connected"}


def test_health_failure(monkeypatch):
    monkeypatch.setattr(services, 'db_sessionmaker', DummySessionMaker(fail=True))
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data.get("status") == "error"
    assert "Connection failed" in data.get("detail", "")
