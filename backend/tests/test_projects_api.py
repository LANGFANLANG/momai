from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app


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


def test_project_crud():
    client = create_client()
    create_response = client.post(
        "/api/projects",
        json={
            "type": "thesis",
            "title": "LifePilot Thesis",
            "major": "Computer Science",
            "school": "Example University",
            "target_word_count": 12000,
            "language": "zh",
            "requirements": "Include experiments.",
        },
    )

    assert create_response.status_code == 201
    project = create_response.json()
    assert project["title"] == "LifePilot Thesis"
    assert project["status"] == "drafting_info"
    project_id = project["id"]

    list_response = client.get("/api/projects")

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [project_id]

    update_response = client.patch(
        f"/api/projects/{project_id}",
        json={"title": "Updated LifePilot Thesis", "target_word_count": 15000},
    )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated LifePilot Thesis"
    assert update_response.json()["target_word_count"] == 15000

    delete_response = client.delete(f"/api/projects/{project_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/api/projects/{project_id}").status_code == 404
