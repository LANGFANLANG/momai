from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())
    assert client.get("/api/health").json() == {"status": "ok"}
