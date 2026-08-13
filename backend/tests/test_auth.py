from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.services.auth import _captcha_challenges


def create_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app = create_app()

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def captcha_payload(client: TestClient) -> dict[str, str]:
    captcha = client.get("/api/auth/captcha")
    assert captcha.status_code == 200
    body = captcha.json()
    assert "code" not in body
    assert body["image"].startswith("data:image/svg+xml;base64,")
    return {"captcha_id": body["id"], "captcha_answer": _captcha_challenges[body["id"]][0]}


def test_default_admin_login_and_project_binding():
    client = create_client()

    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin", **captcha_payload(client)},
    )

    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "Admin project", "language": "zh"},
        headers=headers,
    )
    assert created.status_code == 201
    assert client.get("/api/projects", headers=headers).json()[0]["title"] == "Admin project"


def test_users_only_see_their_own_projects():
    client = create_client()
    alice = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret", **captcha_payload(client)},
    ).json()
    bob = client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "secret", **captcha_payload(client)},
    ).json()
    alice_headers = {"Authorization": f"Bearer {alice['token']}"}
    bob_headers = {"Authorization": f"Bearer {bob['token']}"}

    project = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "Alice project", "language": "zh"},
        headers=alice_headers,
    ).json()

    assert [item["title"] for item in client.get("/api/projects", headers=alice_headers).json()] == ["Alice project"]
    assert client.get("/api/projects", headers=bob_headers).json() == []
    assert client.get(f"/api/projects/{project['id']}", headers=bob_headers).status_code == 404


def test_login_rejects_wrong_captcha():
    client = create_client()
    captcha = client.get("/api/auth/captcha").json()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin",
            "captcha_id": captcha["id"],
            "captcha_answer": "WRONG",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "验证码错误"}
