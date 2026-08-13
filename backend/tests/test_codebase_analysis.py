from pathlib import Path

import pytest

from app.db.models import Project
from app.services.codebase_analyzer import CodebaseAnalysisService


def _sample_project(root: Path) -> None:
    frontend = root / "frontend"
    backend = root / "backend" / "app"
    frontend.mkdir(parents=True)
    backend.mkdir(parents=True)
    (frontend / "package.json").write_text(
        '{"dependencies":{"vue":"^3.5.0","vite":"^6.0.0","pinia":"^2.0.0"}}',
        encoding="utf-8",
    )
    (frontend / "src").mkdir()
    (frontend / "src" / "api.ts").write_text(
        "export const login = () => fetch('/api/auth/login')\n",
        encoding="utf-8",
    )
    (root / "backend" / "pyproject.toml").write_text(
        '[project]\ndependencies=["fastapi", "sqlalchemy"]\n',
        encoding="utf-8",
    )
    (backend / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n@app.post('/api/auth/login')\ndef login(): return {}\n",
        encoding="utf-8",
    )
    (root / "schema.sql").write_text(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT);\n",
        encoding="utf-8",
    )
    (root / ".env").write_text("SECRET_KEY=do-not-read\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")


def test_codebase_analysis_detects_stack_and_skips_sensitive_files(tmp_path):
    _sample_project(tmp_path)

    report = CodebaseAnalysisService.analyze_path(
        tmp_path,
        project_title="登录系统",
        user_hint="本地项目",
    )

    assert "Vue3" in report.tech_stack["frontend"]
    assert "FastAPI" in report.tech_stack["backend"]
    assert "SQLite" in report.tech_stack["database"]
    assert any("登录" in fact.content or "login" in fact.content for fact in report.facts)
    assert all(".env" not in path for fact in report.facts for path in fact.evidence_files)
    assert "node_modules/ignored.js" not in report.file_tree.included_files


def test_apply_analysis_creates_code_summary_material_and_updates_brief(tmp_path, db_session):
    _sample_project(tmp_path)
    project = Project(type="thesis", title="登录系统", language="zh-CN")
    db_session.add(project)
    db_session.commit()

    report = CodebaseAnalysisService.analyze_path(tmp_path, project_title=project.title)
    result = CodebaseAnalysisService.apply_to_project(db_session, project.id, report)

    assert result.material.type == "code_summary"
    assert "Vue3" in result.material.content
    assert project.context is not None
    assert "Vue3" in (project.context.technologies or [])
    assert project.brief is not None
    assert "Vue3" in (project.brief.locked_facts or [])
    assert project.brief.modules


def test_codebase_analysis_rejects_missing_path():
    with pytest.raises(FileNotFoundError):
        CodebaseAnalysisService.analyze_path(Path("Z:/definitely/missing"))
