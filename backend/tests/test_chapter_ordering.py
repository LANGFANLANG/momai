from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.llm import LlmClient
from app.db.base import Base
from app.db.session import get_db
from app.db.models import Chapter, ChapterDraft, ChapterRelation, Project
from app.export.markdown import build_markdown
from app.main import create_app
from app.services.chapters import list_chapters_in_hierarchy_order
from app.services.generation import GenerationService


class NestedOutlineClient(LlmClient):
    def complete_json(self, prompt: str) -> dict:
        return {
            "chapters": [
                {
                    "title": "Second root",
                    "level": 1,
                    "order": 2,
                    "children": [],
                },
                {
                    "title": "First root",
                    "level": 1,
                    "order": 1,
                    "children": [
                        {
                            "title": "Second child",
                            "level": 2,
                            "order": 2,
                            "children": [],
                        },
                        {
                            "title": "First child",
                            "level": 2,
                            "order": 1,
                            "children": [
                                {
                                    "title": "Grandchild",
                                    "level": 3,
                                    "order": 1,
                                    "children": [],
                                }
                            ],
                        },
                    ],
                },
            ]
        }

    def complete_markdown(self, prompt: str) -> str:
        raise AssertionError("Outline should not request Markdown")


def test_nested_outline_generation_and_listing_use_hierarchy_order(db_session):
    project = Project(type="thesis", title="Nested", language="zh")
    db_session.add(project)
    db_session.commit()

    generated = GenerationService.generate_outline(
        db_session, project.id, client=NestedOutlineClient()
    )
    listed = list_chapters_in_hierarchy_order(db_session, project.id)

    expected = [
        "First root",
        "First child",
        "Grandchild",
        "Second child",
        "Second root",
    ]
    assert [chapter.title for chapter in generated] == expected
    assert [chapter.title for chapter in listed] == expected


def test_markdown_export_uses_hierarchy_order_without_duplicate_heading(db_session):
    project = Project(type="thesis", title="Nested export", language="zh")
    root = Chapter(project=project, title="Root", level=1, order=1)
    child = Chapter(project=project, parent=root, title="Child", level=2, order=1)
    draft = ChapterDraft(
        chapter=child,
        version=1,
        content="# Child\n\nBody",
        generation_mode="generate",
    )
    db_session.add_all([project, root, child, draft])
    db_session.commit()

    chapters = list_chapters_in_hierarchy_order(db_session, project.id)
    markdown = build_markdown(project, chapters, {child.id: draft})

    assert markdown.index("# Root") < markdown.index("## Child")
    assert markdown.count("## Child") == 1
    assert "# Child" not in markdown.replace("## Child", "")


def test_relation_listing_uses_chapter_hierarchy_order():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        project = Project(type="thesis", title="Nested relations", language="zh")
        root = Chapter(project=project, title="Root", level=1, order=1)
        child = Chapter(project=project, parent=root, title="Child", level=2, order=1)
        later_root = Chapter(project=project, title="Later root", level=1, order=2)
        relations = [
            ChapterRelation(chapter=later_root, next_bridge="third"),
            ChapterRelation(chapter=child, next_bridge="second"),
            ChapterRelation(chapter=root, next_bridge="first"),
        ]
        db_session.add_all([project, root, child, later_root, *relations])
        db_session.commit()
        project_id = project.id

    def override_get_db():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get(f"/api/projects/{project_id}/relations")

    assert response.status_code == 200
    assert [item["next_bridge"] for item in response.json()] == [
        "first",
        "second",
        "third",
    ]
