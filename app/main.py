from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    ErrorResponse,
    ExportRequest,
    GenerateRequest,
    HealthResponse,
    PortfolioResponse,
    ProfileRequest,
    ProfileResponse,
)
from app.services.github import GitHubService
from app.services.portfolio import (
    build_export_filename,
    build_portfolio_zip,
    generate_portfolio,
    render_portfolio_html,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def get_github_service() -> GitHubService:
    return GitHubService()


def create_app() -> FastAPI:
    app = FastAPI(title="AutoPortfolio Builder", version="0.1.0")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return _error_response(exc.status_code, _status_code_to_error_code(exc.status_code), str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else None
        message = first_error.get("msg", "Request validation failed.") if first_error else "Request validation failed."
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            message,
        )

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

    @app.post("/api/export/html")
    async def export_html(payload: ExportRequest) -> Response:
        filename = build_export_filename(payload)
        html_document = render_portfolio_html(payload.portfolio)
        return Response(
            content=html_document,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.html"'},
        )

    @app.post("/api/export/zip")
    async def export_zip(payload: ExportRequest) -> Response:
        filename = build_export_filename(payload)
        archive_bytes = build_portfolio_zip(payload)
        return Response(
            content=archive_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}.zip"'},
        )

    return app


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse.model_validate({"error": {"code": code, "message": message}})
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _status_code_to_error_code(status_code: int) -> str:
    codes = {
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
        status.HTTP_502_BAD_GATEWAY: "upstream_error",
    }
    return codes.get(status_code, "request_error")


app = create_app()
