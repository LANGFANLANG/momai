# Paper Agent Web MVP

Paper Agent is a local Vue and FastAPI application for drafting papers and reports. PostgreSQL is an external dependency managed by the user; this repository does not start or configure a database container.

## Prerequisites

- Python 3.11 or newer
- Node.js and npm
- PostgreSQL running at `localhost:15432` with:
  - database: `lifepilot`
  - user: `lifepilot`
  - password: `lifepilot`

## Backend Setup

From the repository root, create the local backend environment file and install the backend:

```powershell
Copy-Item backend/.env.example backend/.env
Set-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

`backend/.env` is local-only and must not be committed. The example file contains no secret. The default settings use the user-managed PostgreSQL instance above and the `deepseek-flash` model. To enable real DeepSeek generation, set the `DEEPSEEK_V4` value in `backend/.env`; when it is empty, the app uses deterministic mock generation.

The backend API runs at <http://localhost:8000>. Its health endpoint is <http://localhost:8000/api/health>.

## Frontend Setup

In a second terminal, from the repository root:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open <http://localhost:5173> to use the project list and writing workflow.

## Verification

Backend tests run without PostgreSQL by using SQLite test fixtures:

```powershell
Set-Location backend
python -m pytest -v
```

Build the frontend with:

```powershell
Set-Location frontend
npm run build
```

For a full local run, start PostgreSQL first, apply migrations with `alembic upgrade head`, then run the backend and frontend servers as described above.
