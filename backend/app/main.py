from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ai.json_util import LlmError
from app.api.routers import abstracts, auth, brief, chapters, codebase, export, health, outline, projects, references, relations, review


def create_app() -> FastAPI:
    app = FastAPI(title="Paper Agent API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://11eef8cf.r19.cpolar.top",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(LlmError)
    async def llm_error_handler(_request: Request, exc: LlmError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(brief.router)
    app.include_router(codebase.router)
    app.include_router(abstracts.router)
    app.include_router(references.router)
    app.include_router(outline.router)
    app.include_router(relations.router)
    app.include_router(chapters.router)
    app.include_router(review.router)
    app.include_router(export.router)
    return app


app = create_app()
