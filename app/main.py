from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    GenerateRequest,
    HealthResponse,
    PortfolioResponse,
    ProfileRequest,
    ProfileResponse,
)
from app.services.github import GitHubService
from app.services.portfolio import generate_portfolio


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def get_github_service() -> GitHubService:
    return GitHubService()


def create_app() -> FastAPI:
    app = FastAPI(title="AutoPortfolio Builder", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/api/profile", response_model=ProfileResponse)
    async def profile(
        payload: ProfileRequest,
        github_service: GitHubService = Depends(get_github_service),
    ) -> ProfileResponse:
        return await github_service.fetch_profile(payload.username)

    @app.post("/api/generate", response_model=PortfolioResponse)
    async def generate(payload: GenerateRequest) -> PortfolioResponse:
        return generate_portfolio(payload)

    return app


app = create_app()
