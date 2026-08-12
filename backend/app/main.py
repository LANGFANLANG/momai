from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import brief, chapters, export, health, outline, projects, relations, review


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
    app.include_router(projects.router)
    app.include_router(brief.router)
    app.include_router(outline.router)
    app.include_router(relations.router)
    app.include_router(chapters.router)
    app.include_router(review.router)
    app.include_router(export.router)
    return app


app = create_app()
