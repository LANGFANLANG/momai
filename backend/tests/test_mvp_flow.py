from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.ai.llm import MockLlmClient
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.services import generation


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


def test_full_mvp_api_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    client = create_client()

    project_response = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "Paper Agent", "language": "zh", "target_word_count": 8000},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    context_response = client.put(
        f"/api/projects/{project_id}/context",
        json={"background": "Writing assistant research", "modules": ["outline", "draft"]},
    )
    assert context_response.status_code == 200

    brief_response = client.post(f"/api/projects/{project_id}/brief/generate")
    assert brief_response.status_code == 200
    assert client.patch(f"/api/projects/{project_id}/brief", json={"goal": "Complete the MVP"}).status_code == 200

    outline_response = client.post(f"/api/projects/{project_id}/outline/generate", json={})
    assert outline_response.status_code == 200
    chapters = outline_response.json()
    assert chapters
    chapter_id = chapters[0]["id"]
    assert client.get(f"/api/projects/{project_id}/outline").status_code == 200
    assert client.patch(f"/api/projects/{project_id}/outline/{chapter_id}", json={"purpose": "Introduction"}).status_code == 200

    relations_response = client.post(f"/api/projects/{project_id}/relations/generate")
    assert relations_response.status_code == 200
    relation_id = relations_response.json()[0]["id"]
    assert client.get(f"/api/projects/{project_id}/relations").status_code == 200
    assert client.patch(f"/api/projects/{project_id}/relations/{relation_id}", json={"next_bridge": "Continue"}).status_code == 200

    draft_response = client.post(f"/api/chapters/{chapter_id}/drafts/generate", json={"mode": "generate"})
    assert draft_response.status_code == 200
    assert client.get(f"/api/chapters/{chapter_id}/drafts").status_code == 200
    assert client.post(f"/api/chapters/{chapter_id}/summary/generate").status_code == 200

    review_response = client.post(f"/api/projects/{project_id}/review/generate")
    assert review_response.status_code == 200
    issue_id = review_response.json()[0]["id"]
    assert client.get(f"/api/projects/{project_id}/review").status_code == 200
    assert client.patch(f"/api/projects/{project_id}/review/{issue_id}", json={"status": "fixed"}).status_code == 200

    markdown_response = client.post(f"/api/projects/{project_id}/export/markdown")
    docx_response = client.post(f"/api/projects/{project_id}/export/docx")
    assert markdown_response.status_code == 200
    assert docx_response.status_code == 200
    for response in (markdown_response, docx_response):
        record = response.json()
        assert Path(record["file_url"]).is_file()
        assert client.get(f"/api/exports/{record['id']}/download").status_code == 200

    get_settings.cache_clear()
