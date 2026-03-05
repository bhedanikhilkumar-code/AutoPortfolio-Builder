from __future__ import annotations

from pathlib import Path
import secrets

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    AnalyticsSummary,
    AuthResponse,
    BrandingSettingsRequest,
    BrandingSettingsResponse,
    DashboardResponse,
    DeployExportRequest,
    DeployExportResponse,
    ErrorResponse,
    ExportRequest,
    GenerateRequest,
    HealthResponse,
    LoginRequest,
    LinkedInProfile,
    PortfolioResponse,
    ProfileRequest,
    ProfileResponse,
    RegisterRequest,
    RestoreVersionResponse,
    RewriteRequest,
    RewriteResponse,
    SaveResumeRequest,
    SaveResumeResponse,
    ShareRequest,
    ShareResponse,
    ResumeVersionsResponse,
)
from app.ai_rewrite.service import rewrite_section
from app.analytics.service import get_analytics_for_user, record_page_view, record_project_click
from app.auth.service import create_session, register_user, resolve_user_from_token
from app.branding.service import get_branding, upsert_branding
from app.core.db import init_db
from app.dashboard.service import add_generation_history, build_dashboard, save_resume_snapshot
from app.deploy_export.service import build_deploy_package
from app.resume_versions.service import list_versions, restore_version
from app.services.github import GitHubService
from app.services.linkedin import LinkedInService
from app.services.portfolio import (
    build_export_filename,
    build_portfolio_zip,
    generate_portfolio,
    render_portfolio_pdf,
    render_portfolio_html,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SHARED_PORTFOLIOS: dict[str, PortfolioResponse] = {}


def get_github_service() -> GitHubService:
    return GitHubService()


def get_linkedin_service() -> LinkedInService:
    return LinkedInService()


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
    return resolve_user_from_token(token)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="AutoPortfolio Builder", version="0.2.0")
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

    @app.post("/api/auth/register", response_model=AuthResponse)
    async def auth_register(payload: RegisterRequest) -> AuthResponse:
        register_user(payload.email, payload.password)
        token, _ = create_session(payload.email, payload.password)
        return AuthResponse(access_token=token)

    @app.post("/api/auth/login", response_model=AuthResponse)
    async def auth_login(payload: LoginRequest) -> AuthResponse:
        token, _ = create_session(payload.email, payload.password)
        return AuthResponse(access_token=token)

    @app.get("/api/dashboard", response_model=DashboardResponse)
    async def dashboard(user: dict = Depends(get_current_user)) -> DashboardResponse:
        payload = build_dashboard(user)
        payload.analytics = get_analytics_for_user(user["id"])
        return payload

    @app.post("/api/dashboard/resumes", response_model=SaveResumeResponse)
    async def save_resume(payload: SaveResumeRequest, user: dict = Depends(get_current_user)) -> SaveResumeResponse:
        return save_resume_snapshot(
            user_id=user["id"],
            title=payload.title,
            status=payload.status,
            portfolio_json=payload.portfolio.model_dump_json(),
        )

    @app.get("/api/dashboard/resumes/{resume_id}")
    async def get_resume_for_edit(resume_id: int, user: dict = Depends(get_current_user)) -> JSONResponse:
        from app.core.db import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, title, status, portfolio_json, updated_at FROM resumes WHERE id = ? AND user_id = ?",
                (resume_id, user["id"]),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
            return JSONResponse(
                {
                    "resume_id": int(row["id"]),
                    "title": row["title"],
                    "status": row["status"],
                    "updated_at": row["updated_at"],
                    "portfolio": row["portfolio_json"],
                }
            )
        finally:
            conn.close()

    @app.put("/api/dashboard/resumes/{resume_id}", response_model=SaveResumeResponse)
    async def update_resume(resume_id: int, payload: SaveResumeRequest, user: dict = Depends(get_current_user)) -> SaveResumeResponse:
        from app.core.db import get_connection

        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user["id"])).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

            conn.execute(
                "UPDATE resumes SET title = ?, status = ?, portfolio_json = ?, updated_at = datetime('now') WHERE id = ?",
                (payload.title, payload.status, payload.portfolio.model_dump_json(), resume_id),
            )
            latest = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) AS mx FROM resume_versions WHERE resume_id = ?",
                (resume_id,),
            ).fetchone()
            next_version = int(latest["mx"]) + 1
            conn.execute(
                "INSERT INTO resume_versions(resume_id, version_number, portfolio_json) VALUES(?, ?, ?)",
                (resume_id, next_version, payload.portfolio.model_dump_json()),
            )
            conn.commit()
            return SaveResumeResponse(resume_id=resume_id, message=f"Resume updated. Snapshot v{next_version} created.")
        finally:
            conn.close()

    @app.get("/api/dashboard/resumes/{resume_id}/versions", response_model=ResumeVersionsResponse)
    async def get_resume_versions(resume_id: int, user: dict = Depends(get_current_user)) -> ResumeVersionsResponse:
        return list_versions(user["id"], resume_id)

    @app.post("/api/dashboard/resumes/{resume_id}/restore/{version_number}", response_model=RestoreVersionResponse)
    async def restore_resume_version(resume_id: int, version_number: int, user: dict = Depends(get_current_user)) -> RestoreVersionResponse:
        return restore_version(user["id"], resume_id, version_number)

    @app.post("/api/profile", response_model=ProfileResponse)
    async def profile(
        payload: ProfileRequest,
        github_service: GitHubService = Depends(get_github_service),
        linkedin_service: LinkedInService = Depends(get_linkedin_service),
    ) -> ProfileResponse:
        github_payload = await github_service.fetch_profile(payload.username)
        try:
            linkedin_payload = await linkedin_service.fetch_public_profile(payload.linkedin_username)
            if "not_found" in (linkedin_payload.signals or []):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LinkedIn username not found.")
            if linkedin_payload.provider_used == "slug_inference":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="LinkedIn username not verified. Please enter a valid public LinkedIn username.",
                )
        except HTTPException:
            raise
        except Exception:
            linkedin_slug = payload.linkedin_username.strip().strip("/").split("/")[-1].replace("in/", "")
            linkedin_payload = LinkedInProfile(
                username=linkedin_slug or "unknown",
                url=f"https://www.linkedin.com/in/{linkedin_slug or 'unknown'}/",
                summary=["LinkedIn enrichment temporarily unavailable. GitHub-only mode applied."],
                provider_used="endpoint_fallback",
                confidence_score=0.05,
                signals=["endpoint_fallback"],
            )
        return ProfileResponse(profile=github_payload.profile, repos=github_payload.repos, linkedin=linkedin_payload)

    @app.post("/api/generate", response_model=PortfolioResponse)
    async def generate(payload: GenerateRequest, authorization: str | None = Header(default=None)) -> PortfolioResponse:
        result = generate_portfolio(payload)
        if authorization and authorization.lower().startswith("bearer "):
            try:
                user = resolve_user_from_token(authorization.split(" ", 1)[1].strip())
                add_generation_history(user["id"], payload.profile.username, payload.variant_id, "auto")
            except HTTPException:
                pass
        return result

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

    @app.post("/api/export/pdf")
    async def export_pdf(payload: ExportRequest) -> Response:
        filename = build_export_filename(payload)
        pdf_bytes = render_portfolio_pdf(payload.portfolio, payload.template_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
        )

    @app.post("/api/rewrite", response_model=RewriteResponse)
    async def rewrite(payload: RewriteRequest, user: dict = Depends(get_current_user)) -> RewriteResponse:
        _ = user
        return rewrite_section(payload)

    @app.get("/api/branding", response_model=BrandingSettingsResponse)
    async def branding_get(user: dict = Depends(get_current_user)) -> BrandingSettingsResponse:
        return get_branding(user["id"])

    @app.put("/api/branding", response_model=BrandingSettingsResponse)
    async def branding_put(payload: BrandingSettingsRequest, user: dict = Depends(get_current_user)) -> BrandingSettingsResponse:
        return upsert_branding(user["id"], payload)

    @app.get("/api/analytics", response_model=AnalyticsSummary)
    async def analytics_get(user: dict = Depends(get_current_user)) -> AnalyticsSummary:
        return get_analytics_for_user(user["id"])

    @app.post("/api/deploy/export", response_model=DeployExportResponse)
    async def deploy_export(payload: DeployExportRequest, request: Request, user: dict = Depends(get_current_user)) -> DeployExportResponse:
        _ = user
        filename = payload.filename or "portfolio-deploy"
        package = build_deploy_package(payload)
        SHARED_PORTFOLIOS[filename] = payload.portfolio
        preview_url = str(request.base_url).rstrip("/") + f"/resume/{filename}"
        # store package in memory-less flow by returning preview link only; package can be downloaded via export/zip meanwhile
        _ = package
        return DeployExportResponse(provider=payload.provider, preview_url=preview_url)

    @app.post("/api/share", response_model=ShareResponse)
    async def create_share_link(payload: ShareRequest, request: Request) -> ShareResponse:
        share_id = _new_share_id()
        SHARED_PORTFOLIOS[share_id] = payload.portfolio
        resume_url = str(request.base_url).rstrip("/") + f"/resume/{share_id}"
        share_url = resume_url
        if payload.use_short_link:
            short_url = await _shorten_url(resume_url)
            if short_url:
                share_url = short_url
        return ShareResponse(share_id=share_id, resume_url=resume_url, share_url=share_url)

    @app.get("/resume/{share_id}", include_in_schema=False)
    async def shared_resume(share_id: str) -> Response:
        portfolio = SHARED_PORTFOLIOS.get(share_id)
        if not portfolio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared resume not found.")
        html_document = render_portfolio_html(portfolio)
        return Response(content=html_document, media_type="text/html; charset=utf-8")

    return app


def _new_share_id() -> str:
    while True:
        candidate = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8]
        if candidate and candidate not in SHARED_PORTFOLIOS:
            return candidate


async def _shorten_url(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get("https://tinyurl.com/api-create.php", params={"url": url})
            response.raise_for_status()
            short_url = response.text.strip()
            if short_url.startswith("http://") or short_url.startswith("https://"):
                return short_url
            return None
    except httpx.HTTPError:
        return None


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
