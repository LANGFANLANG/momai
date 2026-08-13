from pathlib import Path
from urllib.parse import unquote

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.ai.llm import LlmClient, MockLlmClient
from app.db.base import Base
from app.db.models import Chapter, ChapterDraft, ExportRecord
from app.db.session import get_db
from app.main import create_app
from app.services import generation


def create_client() -> tuple[TestClient, object]:
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
    return TestClient(app), engine


class VersionedLlmClient(LlmClient):
    def complete_json(self, prompt: str) -> dict:
        return {}

    def complete_markdown(self, prompt: str) -> str:
        return "Draft version 2"


def test_full_mvp_api_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path))
    get_settings.cache_clear()
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    client, engine = create_client()

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
    context_read_response = client.get(f"/api/projects/{project_id}/context")
    assert context_read_response.status_code == 200
    assert context_read_response.json()["background"] == "Writing assistant research"

    brief_response = client.post(f"/api/projects/{project_id}/brief/generate")
    assert brief_response.status_code == 200
    assert client.patch(f"/api/projects/{project_id}/brief", json={"goal": "Complete the MVP"}).status_code == 200
    brief_read_response = client.get(f"/api/projects/{project_id}/brief")
    assert brief_read_response.status_code == 200
    assert brief_read_response.json()["id"] == brief_response.json()["id"]

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
    draft_id = draft_response.json()["id"]
    draft_update_response = client.patch(
        f"/api/chapters/{chapter_id}/drafts/{draft_id}",
        json={"content": "Manually edited draft"},
    )
    assert draft_update_response.status_code == 200
    assert draft_update_response.json()["content"] == "Manually edited draft"
    drafts_after_update = client.get(f"/api/chapters/{chapter_id}/drafts")
    assert drafts_after_update.status_code == 200
    assert drafts_after_update.json()[0]["content"] == "Manually edited draft"
    first_export_response = client.post(f"/api/projects/{project_id}/export/markdown")
    assert first_export_response.status_code == 200
    first_export = first_export_response.json()
    first_draft_content = "Manually edited draft"
    assert Path(first_export["file_url"]).name == "Paper Agent.md"
    assert first_draft_content in Path(first_export["file_url"]).read_text(encoding="utf-8")

    monkeypatch.setattr(generation, "get_llm_client", VersionedLlmClient)
    second_draft_response = client.post(f"/api/chapters/{chapter_id}/drafts/generate", json={"mode": "rewrite"})
    assert second_draft_response.status_code == 200
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    assert client.get(f"/api/chapters/{chapter_id}/drafts").status_code == 200
    summary_response = client.post(f"/api/chapters/{chapter_id}/summary/generate")
    assert summary_response.status_code == 200
    latest_summary_response = client.get(f"/api/chapters/{chapter_id}/summary")
    assert latest_summary_response.status_code == 200
    assert latest_summary_response.json()["id"] == summary_response.json()["id"]

    review_response = client.post(f"/api/projects/{project_id}/review/generate")
    assert review_response.status_code == 200
    issue_id = review_response.json()[0]["id"]
    assert client.get(f"/api/projects/{project_id}/review").status_code == 200
    assert client.patch(f"/api/projects/{project_id}/review/{issue_id}", json={"status": "fixed"}).status_code == 200

    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    second_review = client.post(f"/api/projects/{project_id}/review/generate")
    assert second_review.status_code == 200
    open_issue_id = next(item["id"] for item in second_review.json() if item["status"] == "open")
    fix_response = client.post(f"/api/projects/{project_id}/review/{open_issue_id}/fix")
    assert fix_response.status_code == 200
    assert fix_response.json()["issue"]["status"] == "fixed"
    assert fix_response.json()["drafts"]
    assert "已按一致性建议修订" in fix_response.json()["drafts"][0]["content"]
    closed_fix = client.post(f"/api/projects/{project_id}/review/{open_issue_id}/fix")
    assert closed_fix.status_code == 409

    markdown_response = client.post(f"/api/projects/{project_id}/export/markdown")
    docx_response = client.post(f"/api/projects/{project_id}/export/docx")
    assert markdown_response.status_code == 200
    assert docx_response.status_code == 200
    assert markdown_response.json()["file_url"] != first_export["file_url"]
    assert first_draft_content in Path(first_export["file_url"]).read_text(encoding="utf-8")
    assert "Draft version 2" in Path(markdown_response.json()["file_url"]).read_text(encoding="utf-8")
    for response in (markdown_response, docx_response):
        record = response.json()
        assert Path(record["file_url"]).is_file()
        download = client.get(f"/api/exports/{record['id']}/download")
        assert download.status_code == 200
        assert "Paper Agent" in unquote(download.headers["content-disposition"])

    outside_file = tmp_path.parent / "outside-export.txt"
    outside_file.write_text("outside", encoding="utf-8")
    with Session(engine) as session:
        outside_record = ExportRecord(project_id=project_id, format="markdown", file_url=str(outside_file))
        session.add(outside_record)
        session.commit()
        session.refresh(outside_record)
        outside_export_id = outside_record.id
    assert client.get(f"/api/exports/{outside_export_id}/download").status_code == 404

    get_settings.cache_clear()


def test_outline_regeneration_conflict_preserves_existing_work(monkeypatch):
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    client, engine = create_client()
    project_id = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "Protected outline", "language": "zh"},
    ).json()["id"]
    chapters = client.post(
        f"/api/projects/{project_id}/outline/generate", json={}
    ).json()
    chapter_id = chapters[0]["id"]
    client.post(
        f"/api/chapters/{chapter_id}/drafts/generate", json={"mode": "generate"}
    )

    response = client.post(f"/api/projects/{project_id}/outline/generate", json={})

    assert response.status_code == 409
    assert "force" in response.json()["detail"].lower()
    with Session(engine) as session:
        assert session.get(Chapter, chapter_id) is not None
        assert session.scalar(
            select(func.count()).select_from(ChapterDraft).where(
                ChapterDraft.chapter_id == chapter_id
            )
        ) == 1


def test_summary_generation_without_draft_returns_actionable_409(monkeypatch):
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    client, _ = create_client()
    project_id = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "No draft", "language": "zh"},
    ).json()["id"]
    chapter_id = client.post(
        f"/api/projects/{project_id}/outline/generate", json={}
    ).json()[0]["id"]

    response = client.post(f"/api/chapters/{chapter_id}/summary/generate")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Generate a chapter draft before generating its summary."
    }


def test_paper_abstract_api_generate_get_and_patch(monkeypatch):
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    client, _ = create_client()
    project_id = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "Hive 电商数仓", "language": "zh"},
    ).json()["id"]
    chapter_id = client.post(
        f"/api/projects/{project_id}/outline/generate", json={}
    ).json()[0]["id"]

    missing = client.get(f"/api/projects/{project_id}/abstract")
    assert missing.status_code == 404

    without_draft = client.post(f"/api/projects/{project_id}/abstract/generate")
    assert without_draft.status_code == 409

    client.post(f"/api/chapters/{chapter_id}/drafts/generate", json={"mode": "generate"})
    generated = client.post(f"/api/projects/{project_id}/abstract/generate")
    assert generated.status_code == 200
    body = generated.json()
    assert "本文围绕" in body["abstract_zh"]
    assert body["abstract_en"]
    assert body["keywords_zh"]

    saved = client.patch(
        f"/api/projects/{project_id}/abstract",
        json={
            "abstract_zh": "手工修改后的中文摘要。",
            "keywords_zh": ["Hive", "电商"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["abstract_zh"] == "手工修改后的中文摘要。"
    assert saved.json()["id"] == body["id"]

    fetched = client.get(f"/api/projects/{project_id}/abstract")
    assert fetched.status_code == 200
    assert fetched.json()["abstract_zh"] == "手工修改后的中文摘要。"
    assert fetched.json()["keywords_zh"] == ["Hive", "电商"]

    markdown = client.post(f"/api/projects/{project_id}/export/markdown")
    assert markdown.status_code == 200
    content = Path(markdown.json()["file_url"]).read_text(encoding="utf-8")
    assert content.index("# 摘要") < content.index("# Abstract")
    assert "手工修改后的中文摘要。" in content
    assert "关键词：Hive；电商" in content


def test_reference_api_crud(monkeypatch):
    monkeypatch.setattr(generation, "get_llm_client", MockLlmClient)
    client, _ = create_client()
    project_id = client.post(
        "/api/projects",
        json={"type": "thesis", "title": "Cite Hive", "language": "zh"},
    ).json()["id"]

    created = client.post(
        f"/api/projects/{project_id}/references",
        json={
            "authors": "乙",
            "title": "Hive 实践",
            "source": "软件学报",
            "year": "2021",
        },
    )
    assert created.status_code == 201
    ref_id = created.json()["id"]
    listed = client.get(f"/api/projects/{project_id}/references")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Hive 实践"

    updated = client.patch(
        f"/api/projects/{project_id}/references/{ref_id}",
        json={"year": "2022"},
    )
    assert updated.status_code == 200
    assert updated.json()["year"] == "2022"

    deleted = client.delete(f"/api/projects/{project_id}/references/{ref_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/projects/{project_id}/references").json() == []
