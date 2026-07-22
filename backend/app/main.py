from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import geometry, projects
from .config import get_settings
from .importers import supported_extensions

app = FastAPI(
    title="AI Defeaturing Review",
    version="0.1.0",
    description="Compares an original CAD model with a defeatured one and documents every change.",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(geometry.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "version": app.version,
        "llm_provider": settings.llm_provider,
        "supported_formats": supported_extensions(),
    }
