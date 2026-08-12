# Paper Agent Web MVP Design

## Goal

Build the MVP for the paper/report writing Agent web application described in `docs/论文报告写作Agent-Web应用设计文档.md` and `docs/论文报告写作Agent-项目架构文档.md`.

The MVP should let a user create a writing project, fill project context, generate and edit a Project Brief, generate and edit an outline, generate chapter relations, draft chapters, summarize chapters, run a consistency review, and export Markdown or Word files.

## Confirmed Constraints

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

## Architecture

The project will be scaffolded as a frontend/backend monorepo:

```text
frontend/
  Vue application for the writing workflow.

backend/
  FastAPI application with REST APIs, SQLAlchemy models, Alembic migrations,
  LangGraph workflow modules, and export services.

docs/
  Product documents, Superpowers specs, and implementation plans.
```

The backend owns persistence, generation workflow orchestration, and export files. The frontend owns workflow navigation, forms, editable content, and user feedback.

AI workflow modules expose stable service methods even when the real DeepSeek call is unavailable. This keeps the domain flow independent from provider availability.

## Backend Design

The backend will expose these route groups:

- `/api/health`
- `/api/projects`
- `/api/projects/{project_id}/context`
- `/api/projects/{project_id}/brief`
- `/api/projects/{project_id}/outline`
- `/api/projects/{project_id}/relations`
- `/api/chapters/{chapter_id}/drafts`
- `/api/chapters/{chapter_id}/summary`
- `/api/projects/{project_id}/review`
- `/api/projects/{project_id}/export`
- `/api/exports/{export_id}/download`

The database model follows the docs:

- `projects`
- `project_contexts`
- `project_briefs`
- `chapters`
- `chapter_relations`
- `chapter_drafts`
- `chapter_summaries`
- `materials`
- `feedback_items`
- `consistency_issues`
- `export_records`

Authentication is intentionally deferred for the first local MVP. To preserve future ownership boundaries, `projects.user_id` will exist and default to a local development user id. Later JWT auth can replace this without reshaping project-owned data.

## AI Design

The backend will include a provider abstraction:

```python
class LlmClient:
    def complete_json(self, prompt: str) -> dict: ...
    def complete_markdown(self, prompt: str) -> str: ...
```

`DeepSeekClient` reads:

- `DEEPSEEK_V4`
- `DEEPSEEK_BASE_URL`, default `https://api.deepseek.com`
- `DEEPSEEK_MODEL`, default `deepseek-flash`

`MockLlmClient` is selected automatically when `DEEPSEEK_V4` is missing.

LangGraph graph modules will exist for:

- Brief generation
- Outline generation
- Relation generation
- Chapter draft generation
- Chapter summary generation
- Consistency review

Each graph loads context, builds a prompt, calls the LLM client, validates or normalizes the response, and persists the result through service methods.

## Frontend Design

The first screen is the actual project list, not a marketing landing page.

Routes:

- `/projects`
- `/projects/new`
- `/projects/:projectId/brief`
- `/projects/:projectId/outline`
- `/projects/:projectId/relations`
- `/projects/:projectId/chapters/:chapterId`
- `/projects/:projectId/review`
- `/projects/:projectId/export`

UI style should feel like a writing operations tool: dense, quiet, scan-friendly, and focused. Pages use full-width application layouts, side navigation for project workflow steps, compact forms, and editable panels. Cards are reserved for repeated project or issue items.

## Data Flow

1. User creates a project.
2. User saves project context.
3. Backend generates or updates Project Brief.
4. Backend generates outline chapters.
5. User edits and confirms outline.
6. Backend generates chapter relations.
7. User generates drafts chapter by chapter.
8. Backend stores draft versions and summaries.
9. Backend runs consistency review over brief, outline, relations, and latest drafts.
10. Backend exports Markdown or Word and records the export.

## Error Handling

- Database errors return structured HTTP errors.
- Missing project or chapter returns `404`.
- AI JSON parse failure falls back to deterministic normalized output where possible.
- AI provider failure returns an actionable error while preserving existing user content.
- Export failure leaves previous export records untouched.

## Testing

Backend tests cover:

- Project creation and update.
- Brief, outline, relation, draft, summary, review, and export services using mock LLM.
- Markdown export.
- Word export file creation.

Frontend tests are scoped to basic route rendering and core store/API behavior if the local toolchain supports it.

Manual verification covers:

- Backend starts and health endpoint responds.
- Frontend starts and reaches project list.
- A full local writing flow completes using mock generation.

## Notes

The current workspace is not a git repository, so the Superpowers-required spec commit cannot be performed until a git repository is initialized or this work is moved into one.
