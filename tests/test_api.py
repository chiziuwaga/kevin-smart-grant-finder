from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app and services mapping
test_app = __import__('Home').main_app
services = __import__('Home').services

client = TestClient(test_app)

class DummyMongoClient:
    def __init__(self, fail=False):
        if fail:
            def cmd(cmd):
                raise Exception("Connection failed")
            self.client = SimpleNamespace(admin=SimpleNamespace(command=cmd))
        else:
            self.client = SimpleNamespace(admin=SimpleNamespace(command=lambda cmd: {}))


def test_health_success(monkeypatch):
    # Simulate successful MongoDB ping
    monkeypatch.setitem(services, 'mongodb_client', DummyMongoClient(fail=False))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "detail": "MongoDB connected"}


def test_health_failure(monkeypatch):
    # Simulate MongoDB ping failure
    monkeypatch.setitem(services, 'mongodb_client', DummyMongoClient(fail=True))
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data.get("status") == "error"
    assert "Connection failed" in data.get("detail", "") 