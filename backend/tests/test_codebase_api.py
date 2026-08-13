from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Project
from app.db.session import get_db
from app.main import create_app
from app.services.auth import AuthService, ensure_default_admin


def _sample_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        '{"dependencies":{"vue":"^3.5.0","vite":"^6.0.0"}}',
        encoding="utf-8",
    )
    (root / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )


def test_codebase_api_analyzes_and_applies_to_project(tmp_path):
    code_root = tmp_path / "code"
    _sample_project(code_root)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = ensure_default_admin(session)
        project = Project(type="thesis", title="本地项目论文", language="zh-CN", user=user)
        session.add_all([user, project])
        session.commit()
        project_id = project.id
        token = AuthService.create_session(user)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/projects/{project_id}/codebase/analyze",
        json={"root_path": str(code_root)},
        headers=headers,
    )

    assert response.status_code == 200
    analysis = response.json()
    assert "Vue3" in analysis["tech_stack"]["frontend"]

    apply_response = client.post(
        f"/api/projects/{project_id}/codebase/apply",
        json={"analysis": analysis},
        headers=headers,
    )

    assert apply_response.status_code == 200
    body = apply_response.json()
    assert body["material_id"]
    assert body["brief_updated"] is True
