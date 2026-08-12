# Paper Agent Web MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MVP for the paper/report writing Agent web app with Vue frontend, FastAPI backend, PostgreSQL persistence, DeepSeek-compatible generation, mock fallback, and Markdown/Word export.

**Architecture:** Create a frontend/backend monorepo. The backend owns data, AI workflow orchestration, and exports through route/service/model boundaries; the frontend owns the writing workflow UI and calls REST APIs through typed clients. LangGraph modules are present behind service methods, with DeepSeek used when `DEEPSEEK_V4` exists and deterministic mock generation otherwise.

**Tech Stack:** Vue3, Vite, TypeScript, Pinia, Vue Router, Tailwind CSS, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, LangGraph, PostgreSQL, psycopg, python-docx, pytest.

## Global Constraints

- Backend remains the original documented stack: FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, LangGraph.
- Frontend uses Vue3, Vite, TypeScript, Pinia, Vue Router, and Tailwind CSS.
- PostgreSQL is provided by the user and is not managed by this project.
- Backend database URL is `postgresql+psycopg://lifepilot:lifepilot@localhost:15432/lifepilot`.
- DeepSeek is the LLM provider.
- Default model is `deepseek-flash`.
- The API key is read from environment variable `DEEPSEEK_V4`.
- The backend must not hard-code secrets.
- If `DEEPSEEK_V4` is absent, AI workflows fall back to deterministic mock generation so the app remains usable locally.
- The MVP does not include plagiarism detection, real literature retrieval, multi-user collaboration, payments, LaTeX export, deep code repository analysis, or school template recognition.
- Current workspace is not a git repository, so commit steps are skipped unless a git repository is initialized before execution.

---

## File Structure

Create:

- `backend/pyproject.toml` - Python package metadata and dependencies.
- `backend/.env.example` - documented backend environment variables without secrets.
- `backend/alembic.ini` - Alembic configuration.
- `backend/alembic/env.py` - migration environment wired to SQLAlchemy metadata.
- `backend/alembic/versions/20260812_0001_initial_schema.py` - initial schema migration.
- `backend/app/main.py` - FastAPI app factory and router registration.
- `backend/app/core/config.py` - settings object reading `DATABASE_URL`, `DEEPSEEK_V4`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`.
- `backend/app/db/session.py` - SQLAlchemy engine/session dependency.
- `backend/app/db/base.py` - declarative base export.
- `backend/app/db/models.py` - all MVP SQLAlchemy models and enums.
- `backend/app/schemas/*.py` - Pydantic request/response schemas.
- `backend/app/services/*.py` - project, generation, review, and export service logic.
- `backend/app/ai/llm.py` - DeepSeek and mock LLM clients.
- `backend/app/ai/prompts.py` - prompt templates copied from the docs and adapted to Python formatting.
- `backend/app/ai/graphs.py` - LangGraph workflow builders.
- `backend/app/api/deps.py` - database dependency helpers.
- `backend/app/api/routers/*.py` - REST route groups.
- `backend/app/export/markdown.py` - Markdown export builder.
- `backend/app/export/docx.py` - Word export builder.
- `backend/tests/test_mvp_flow.py` - backend integration test using mock LLM and SQLite test database.
- `frontend/package.json` - frontend scripts and dependencies.
- `frontend/index.html` - Vite entry HTML.
- `frontend/vite.config.ts` - Vite config.
- `frontend/tsconfig.json` - TypeScript config.
- `frontend/tailwind.config.ts` - Tailwind config.
- `frontend/postcss.config.cjs` - PostCSS config.
- `frontend/src/main.ts` - Vue app entry.
- `frontend/src/App.vue` - application shell.
- `frontend/src/router/index.ts` - route definitions.
- `frontend/src/api/*.ts` - typed API clients.
- `frontend/src/stores/*.ts` - Pinia stores.
- `frontend/src/types/*.ts` - shared frontend types.
- `frontend/src/pages/*.vue` - workflow pages.
- `frontend/src/styles/index.css` - Tailwind and app styles.
- `README.md` - local setup, database expectations, DeepSeek env, and verification commands.

Modify:

- `docs/superpowers/specs/2026-08-12-paper-agent-web-design.md` only if implementation reveals a design contradiction.

---

### Task 1: Backend Project Scaffold And Configuration

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routers/__init__.py`
- Create: `backend/app/api/routers/health.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `get_settings() -> Settings`
- Produces: `get_db() -> Iterator[Session]`
- Produces: `create_app() -> FastAPI`
- Produces: `GET /api/health -> {"status": "ok"}`

- [ ] **Step 1: Create backend package files**

Add `backend/pyproject.toml`:

```toml
[project]
name = "paper-agent-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.116.0",
  "uvicorn[standard]>=0.30.0",
  "sqlalchemy>=2.0.30",
  "psycopg[binary]>=3.2.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.3.0",
  "alembic>=1.13.0",
  "langgraph>=0.2.0",
  "httpx>=0.27.0",
  "python-docx>=1.1.2",
  "pytest>=8.2.0",
  "pytest-asyncio>=0.23.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Add `backend/.env.example`:

```env
DATABASE_URL=postgresql+psycopg://lifepilot:lifepilot@localhost:15432/lifepilot
DEEPSEEK_V4=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
EXPORT_DIR=./exports
```

- [ ] **Step 2: Create settings and database session**

Add `backend/app/core/config.py`:

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://lifepilot:lifepilot@localhost:15432/lifepilot"
    deepseek_v4: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    export_dir: str = "./exports"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Add `backend/app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Add `backend/app/db/session.py`:

```python
from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import get_settings


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Create FastAPI app and health route**

Add `backend/app/api/routers/health.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Add `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="Paper Agent API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 4: Add health tests**

Add `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())
    assert client.get("/api/health").json() == {"status": "ok"}
```

- [ ] **Step 5: Run backend health tests**

Run: `cd backend; python -m pytest tests/test_health.py -v`

Expected: 1 passing test.

---

### Task 2: Backend Data Model And Alembic Migration

**Files:**
- Create: `backend/app/db/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260812_0001_initial_schema.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `Base` from `app.db.base`
- Produces: ORM classes `Project`, `ProjectContext`, `ProjectBrief`, `Chapter`, `ChapterRelation`, `ChapterDraft`, `ChapterSummary`, `Material`, `FeedbackItem`, `ConsistencyIssue`, `ExportRecord`

- [ ] **Step 1: Add SQLAlchemy models**

Add models with UUID string primary keys, enum columns, JSON columns for list/dict fields, UTC timestamps, relationships, and cascade deletion from `Project` to owned records. Use these enum values exactly:

```python
PROJECT_TYPES = ("course_report", "thesis", "proposal")
PROJECT_STATUSES = ("drafting_info", "brief_ready", "outline_ready", "relations_ready", "drafting_chapters", "review_ready", "export_ready")
CHAPTER_STATUSES = ("planned", "relation_ready", "drafting", "drafted", "reviewed")
DRAFT_MODES = ("generate", "rewrite", "continue", "expand", "compress", "polish")
MATERIAL_TYPES = ("requirement", "code_summary", "database_schema", "experiment_data", "reference", "advisor_feedback", "template", "other")
FEEDBACK_STATUSES = ("open", "applied", "ignored")
ISSUE_SEVERITIES = ("low", "medium", "high")
ISSUE_STATUSES = ("open", "fixed", "ignored")
EXPORT_FORMATS = ("markdown", "docx", "pdf", "latex")
```

- [ ] **Step 2: Add Alembic configuration**

Set `sqlalchemy.url = postgresql+psycopg://lifepilot:lifepilot@localhost:15432/lifepilot` in `backend/alembic.ini`.

In `backend/alembic/env.py`, import `Base` and `app.db.models`, set `target_metadata = Base.metadata`, and read the runtime URL from `get_settings().database_url`.

- [ ] **Step 3: Add initial migration**

Create all tables listed in the design. Use PostgreSQL `JSON` columns for list/dict fields and `String(36)` ids.

- [ ] **Step 4: Add model creation test**

Add `backend/tests/test_models.py` with an in-memory SQLite engine that creates `Base.metadata`, inserts a `Project`, flushes it, and verifies defaults:

```python
def test_project_defaults_to_drafting_info(db_session):
    project = Project(type="thesis", title="LifePilot 论文", language="zh")
    db_session.add(project)
    db_session.flush()
    assert project.status == "drafting_info"
    assert project.user_id == "local-dev-user"
```

- [ ] **Step 5: Run model tests**

Run: `cd backend; python -m pytest tests/test_models.py -v`

Expected: model tests pass without requiring the user's PostgreSQL container.

---

### Task 3: Backend Schemas, Project Service, And Project Routes

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/projects.py`
- Create: `backend/app/api/routers/projects.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_projects_api.py`

**Interfaces:**
- Produces: `ProjectService.create_project(db, payload) -> Project`
- Produces: `POST /api/projects`
- Produces: `GET /api/projects`
- Produces: `GET /api/projects/{project_id}`
- Produces: `PATCH /api/projects/{project_id}`
- Produces: `DELETE /api/projects/{project_id}`

- [ ] **Step 1: Add project schemas**

Create request schemas for create/update and response schemas with `from_attributes=True`. Include fields `id`, `type`, `title`, `major`, `school`, `target_word_count`, `language`, `requirements`, `status`, `created_at`, `updated_at`.

- [ ] **Step 2: Add project service**

Implement create/list/get/update/delete. `get_project_or_404` raises `fastapi.HTTPException(status_code=404, detail="Project not found")`.

- [ ] **Step 3: Add project router**

Wire routes under `/api/projects`, inject `Session` through `get_db`, and call the service.

- [ ] **Step 4: Register router**

Modify `backend/app/main.py`:

```python
from app.api.routers import health, projects

app.include_router(projects.router)
```

- [ ] **Step 5: Add API tests**

Test create, list, update, and delete with SQLite dependency override. Verify delete removes the project from later GET.

- [ ] **Step 6: Run project API tests**

Run: `cd backend; python -m pytest tests/test_projects_api.py -v`

Expected: project API tests pass.

---

### Task 4: Backend AI Client, Prompts, And Generation Services

**Files:**
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/llm.py`
- Create: `backend/app/ai/prompts.py`
- Create: `backend/app/ai/graphs.py`
- Create: `backend/app/schemas/brief.py`
- Create: `backend/app/schemas/chapter.py`
- Create: `backend/app/schemas/review.py`
- Create: `backend/app/services/generation.py`
- Create: `backend/tests/test_generation_services.py`

**Interfaces:**
- Produces: `get_llm_client() -> LlmClient`
- Produces: `GenerationService.generate_brief(db, project_id) -> ProjectBrief`
- Produces: `GenerationService.generate_outline(db, project_id, outline_preference) -> list[Chapter]`
- Produces: `GenerationService.generate_relations(db, project_id) -> list[ChapterRelation]`
- Produces: `GenerationService.generate_draft(db, chapter_id, mode, user_instruction) -> ChapterDraft`
- Produces: `GenerationService.generate_summary(db, chapter_id) -> ChapterSummary`
- Produces: `GenerationService.review_consistency(db, project_id) -> list[ConsistencyIssue]`

- [ ] **Step 1: Add LLM abstraction**

Implement `LlmClient`, `DeepSeekClient`, and `MockLlmClient`. `DeepSeekClient` must send OpenAI-compatible chat completions to `{base_url}/chat/completions` with model `deepseek-flash`. `get_llm_client()` returns `MockLlmClient` when `DEEPSEEK_V4` is empty.

- [ ] **Step 2: Add prompt templates**

Copy the documented prompt templates into named constants:

```python
BRIEF_PROMPT
OUTLINE_PROMPT
RELATION_PROMPT
CHAPTER_DRAFT_PROMPT
CHAPTER_SUMMARY_PROMPT
CONSISTENCY_REVIEW_PROMPT
```

Use Python `.format(...)` placeholders.

- [ ] **Step 3: Add LangGraph wrappers**

Create workflow builders that call service node functions in order. If LangGraph import or graph execution becomes incompatible during implementation, keep the public graph builder functions and call the same node sequence directly in tests.

- [ ] **Step 4: Add generation service**

Generate deterministic mock values when using `MockLlmClient`:

```python
brief.background = context.background or "围绕项目主题整理研究背景。"
outline = ["绪论", "相关理论与技术基础", "需求分析", "系统设计", "系统实现", "测试与结果分析", "总结与展望", "参考文献"]
draft.content starts with "# {chapter.title}"
summary.summary = "{chapter.title}概述了本章的核心内容。"
issue.type = "structure_review"
```

- [ ] **Step 5: Add service tests**

Create one project with context, generate brief, outline, relations, first chapter draft, summary, and review issues. Assert persisted rows exist after each step.

- [ ] **Step 6: Run generation tests**

Run: `cd backend; python -m pytest tests/test_generation_services.py -v`

Expected: generation tests pass with no DeepSeek key.

---

### Task 5: Backend Workflow Routes And Export Services

**Files:**
- Create: `backend/app/api/routers/brief.py`
- Create: `backend/app/api/routers/outline.py`
- Create: `backend/app/api/routers/relations.py`
- Create: `backend/app/api/routers/chapters.py`
- Create: `backend/app/api/routers/review.py`
- Create: `backend/app/api/routers/export.py`
- Create: `backend/app/export/__init__.py`
- Create: `backend/app/export/markdown.py`
- Create: `backend/app/export/docx.py`
- Create: `backend/app/services/export.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_mvp_flow.py`

**Interfaces:**
- Produces: all REST endpoints named in the design.
- Produces: `ExportService.export_markdown(db, project_id) -> ExportRecord`
- Produces: `ExportService.export_docx(db, project_id) -> ExportRecord`

- [ ] **Step 1: Add workflow routers**

Expose context save, brief generate/update, outline generate/list/update, relations generate/list/update, draft generate/list, summary generate, review generate/list/update.

- [ ] **Step 2: Add Markdown export**

Build Markdown by sorting chapters by `order`, writing headings using `#` repeated by chapter level, and appending latest draft content under each heading.

- [ ] **Step 3: Add Word export**

Use `python-docx` to create a `.docx`, write project title, chapter headings, and latest draft content. Save into `EXPORT_DIR`.

- [ ] **Step 4: Add export router**

Expose:

```text
POST /api/projects/{project_id}/export/markdown
POST /api/projects/{project_id}/export/docx
GET /api/exports/{export_id}/download
```

- [ ] **Step 5: Add full MVP flow API test**

The test creates a project, saves context, generates brief, outline, relations, draft, summary, review, Markdown export, and Word export. Assert each endpoint returns `200` or `201` and export files exist.

- [ ] **Step 6: Run backend suite**

Run: `cd backend; python -m pytest -v`

Expected: all backend tests pass without PostgreSQL by overriding the database in tests.

---

### Task 6: Frontend Scaffold, Routing, API Clients, And Stores

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.cjs`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/api/http.ts`
- Create: `frontend/src/api/projects.ts`
- Create: `frontend/src/api/workflow.ts`
- Create: `frontend/src/stores/project.ts`
- Create: `frontend/src/stores/chapter.ts`
- Create: `frontend/src/types/project.ts`
- Create: `frontend/src/types/chapter.ts`
- Create: `frontend/src/styles/index.css`

**Interfaces:**
- Produces: `npm run dev`
- Produces: `npm run build`
- Produces: typed API methods for every backend route used by pages.

- [ ] **Step 1: Add frontend dependencies**

`frontend/package.json` scripts:

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --host 0.0.0.0"
  }
}
```

Dependencies: `@vitejs/plugin-vue`, `vite`, `vue`, `vue-router`, `pinia`, `typescript`, `vue-tsc`, `tailwindcss`, `postcss`, `autoprefixer`, `lucide-vue-next`.

- [ ] **Step 2: Add app shell and routes**

Routes must redirect `/` to `/projects` and define all workflow paths from the design.

- [ ] **Step 3: Add HTTP client**

`frontend/src/api/http.ts` exports:

```ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export async function request<T>(path: string, init?: RequestInit): Promise<T>
```

Throw an `Error` with response text for non-2xx responses.

- [ ] **Step 4: Add Pinia stores**

`projectStore` loads project list/current project and exposes create/update/delete. `chapterStore` loads chapters, relations, drafts, summaries, and review issues.

- [ ] **Step 5: Run frontend build**

Run: `cd frontend; npm install; npm run build`

Expected: production build succeeds.

---

### Task 7: Frontend Workflow Pages

**Files:**
- Create: `frontend/src/pages/ProjectListPage.vue`
- Create: `frontend/src/pages/ProjectCreatePage.vue`
- Create: `frontend/src/pages/ProjectLayout.vue`
- Create: `frontend/src/pages/ProjectBriefPage.vue`
- Create: `frontend/src/pages/OutlinePage.vue`
- Create: `frontend/src/pages/ChapterRelationsPage.vue`
- Create: `frontend/src/pages/ChapterWritingPage.vue`
- Create: `frontend/src/pages/ConsistencyReviewPage.vue`
- Create: `frontend/src/pages/ExportPage.vue`
- Create: `frontend/src/components/ui/AppButton.vue`
- Create: `frontend/src/components/ui/AppField.vue`

**Interfaces:**
- Consumes: stores and API clients from Task 6.
- Produces: usable pages for the full writing flow.

- [ ] **Step 1: Build project list and create pages**

Project list shows title, type, status, updated time, and open/delete actions. Create page includes type, title, major, school, target word count, language, and requirements.

- [ ] **Step 2: Build project layout**

Add a left workflow nav with Brief, Outline, Relations, Writing, Review, Export. The nav uses compact text and active route styling.

- [ ] **Step 3: Build Brief page**

Include grouped textareas for background, problem, goal, scenario, target users, technologies, modules, architecture, environment, experiments, and writing preferences. Provide save context and generate brief actions.

- [ ] **Step 4: Build Outline page**

Show editable chapter rows with title, level, purpose, suggested word count, and status. Provide generate outline and save outline actions.

- [ ] **Step 5: Build Relations page**

Show chapter list, relation editor, and context preview. Provide generate relations and save selected relation actions.

- [ ] **Step 6: Build Writing page**

Show outline navigation, Markdown textarea editor, generation controls for mode/user instruction, latest drafts, and summary generation.

- [ ] **Step 7: Build Review and Export pages**

Review page runs consistency check and lists issues. Export page previews combined draft text and provides Markdown/Word export buttons.

- [ ] **Step 8: Run frontend build**

Run: `cd frontend; npm run build`

Expected: production build succeeds and no page has TypeScript errors.

---

### Task 8: Documentation And Local Verification

**Files:**
- Create: `README.md`
- Modify: `backend/.env.example`
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: clear local run instructions for a user-managed PostgreSQL container.

- [ ] **Step 1: Write README**

Include:

```text
1. Start PostgreSQL yourself at localhost:15432 with database/user/password lifepilot.
2. Backend env: copy backend/.env.example to backend/.env.
3. Set DEEPSEEK_V4 when real DeepSeek generation is desired.
4. Backend setup: cd backend; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -e .; alembic upgrade head; uvicorn app.main:app --reload
5. Frontend setup: cd frontend; npm install; npm run dev
6. Open http://localhost:5173
```

- [ ] **Step 2: Verify backend**

Run: `cd backend; python -m pytest -v`

Expected: all backend tests pass.

- [ ] **Step 3: Verify frontend**

Run: `cd frontend; npm run build`

Expected: frontend build passes.

- [ ] **Step 4: Verify runtime health**

If dependencies are installed, run backend server and frontend dev server. Check:

```text
GET http://localhost:8000/api/health -> {"status":"ok"}
http://localhost:5173 -> project list page
```

- [ ] **Step 5: Record verification result**

Add a short note to the final response with exact commands that passed and commands that could not run because dependencies or PostgreSQL were unavailable.
