from __future__ import annotations

from pathlib import Path
import logging
import os
import secrets
import time

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    AdminActionResponse,
    AdminActivityResponse,
    AdminResumesResponse,
    AdminStatsResponse,
    AdminUsersResponse,
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
    GitHubAuthStartResponse,
    GoogleAccessTokenRequest,
    GoogleAuthConfigResponse,
    GoogleAuthStartResponse,
    GoogleAuthRequest,
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
from app.admin.service import (
    delete_resume_admin,
    export_admin_activity_csv,
    export_admin_resumes_csv,
    export_admin_users_csv,
    force_publish_resume,
    get_admin_activity,
    get_admin_resumes_overview,
    get_admin_stats,
    get_admin_users_overview,
)
from app.ai_rewrite.service import rewrite_section
from app.analytics.service import get_analytics_for_user, record_page_view, record_project_click
from app.auth.github import exchange_github_code, fetch_github_identity, get_github_client_id
from app.auth.google import (
    build_google_auth_url,
    exchange_google_code,
    get_google_client_id,
    verify_google_access_token,
    verify_google_id_token,
)
from app.auth.service import create_session, create_session_for_user, ensure_user_for_google, register_user, resolve_user_from_token, revoke_session
from app.branding.service import get_branding, upsert_branding
from app.core.db import init_db
from app.dashboard.service import add_generation_history, build_dashboard, save_resume_snapshot
from app.deploy_export.service import build_deploy_package
from app.resume_versions.service import list_versions, restore_version
from app.services.github import GitHubService, normalize_github_username
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
GITHUB_OAUTH_STATES: dict[str, float] = {}
GOOGLE_OAUTH_STATES: dict[str, float] = {}
logger = logging.getLogger("autoporfolio_builder")


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


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


def _google_redirect_uri(request: Request) -> str:
    configured = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return str(request.base_url).rstrip("/") + "/api/auth/google/callback"


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

    def _spa_entry() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return _spa_entry()

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon_ico() -> FileResponse:
        return FileResponse(STATIC_DIR / "assets" / "favicon.ico", headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/favicon-32x32.png", include_in_schema=False)
    async def favicon_32() -> FileResponse:
        return FileResponse(STATIC_DIR / "assets" / "favicon-32.png", headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/favicon-16x16.png", include_in_schema=False)
    async def favicon_16() -> FileResponse:
        return FileResponse(STATIC_DIR / "assets" / "favicon-16.png", headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/login", include_in_schema=False)
    async def login_page() -> FileResponse:
        return _spa_entry()

    @app.get("/signup", include_in_schema=False)
    async def signup_page() -> FileResponse:
        return _spa_entry()

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard_page() -> FileResponse:
        return _spa_entry()

    @app.get("/generator", include_in_schema=False)
    async def generator_page() -> FileResponse:
        return _spa_entry()

    @app.get("/admin", include_in_schema=False)
    async def admin_page() -> FileResponse:
        return _spa_entry()

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/api/auth/register", response_model=AuthResponse)
    async def auth_register(payload: RegisterRequest) -> AuthResponse:
        register_user(payload.name, payload.email, payload.password)
        token, _ = create_session(payload.email, payload.password)
        return AuthResponse(access_token=token)

    @app.post("/api/auth/login", response_model=AuthResponse)
    async def auth_login(payload: LoginRequest) -> AuthResponse:
        token, _ = create_session(payload.email, payload.password)
        return AuthResponse(access_token=token)

    @app.post("/api/auth/logout", response_model=AuthResponse)
    async def auth_logout(user: dict = Depends(get_current_user), authorization: str | None = Header(default=None)) -> AuthResponse:
        _ = user
        token = authorization.split(" ", 1)[1].strip() if authorization else ""
        if token:
            revoke_session(token)
        return AuthResponse(access_token="logged_out")

    @app.get("/api/auth/google/config", response_model=GoogleAuthConfigResponse)
    async def auth_google_config() -> GoogleAuthConfigResponse:
        client_id = get_google_client_id()
        return GoogleAuthConfigResponse(enabled=bool(client_id), client_id=client_id or None)

    @app.get("/api/auth/google/start", response_model=GoogleAuthStartResponse)
    async def auth_google_start(request: Request) -> GoogleAuthStartResponse:
        client_id = get_google_client_id()
        if not client_id:
            return GoogleAuthStartResponse(enabled=False, auth_url=None)

        state = secrets.token_urlsafe(24)
        GOOGLE_OAUTH_STATES[state] = time.time() + 600
        for key, expires in list(GOOGLE_OAUTH_STATES.items()):
            if expires < time.time():
                GOOGLE_OAUTH_STATES.pop(key, None)

        redirect_uri = _google_redirect_uri(request)
        auth_url = build_google_auth_url(redirect_uri=redirect_uri, state=state)
        return GoogleAuthStartResponse(enabled=True, auth_url=auth_url)

    @app.get("/api/auth/google/callback", include_in_schema=False)
    async def auth_google_callback(request: Request, code: str | None = None, state: str | None = None) -> Response:
        if not code or not state:
            return Response(content="Google login failed: missing code/state.", media_type="text/plain", status_code=400)
        expires = GOOGLE_OAUTH_STATES.pop(state, None)
        if not expires or expires < time.time():
            return Response(content="Google login failed: invalid or expired state.", media_type="text/plain", status_code=400)

        redirect_uri = _google_redirect_uri(request)
        try:
            google_user = await exchange_google_code(code, redirect_uri)
            user_id = ensure_user_for_google(google_user["email"], google_user.get("name"), google_user.get("avatar_url"))
            app_token = create_session_for_user(user_id)
        except HTTPException as exc:
            return Response(content=f"Google login failed: {exc.detail}", media_type="text/plain", status_code=400)

        html = f"""
        <!doctype html><html><body><script>
        try {{
          localStorage.removeItem('apb_token');
          sessionStorage.setItem('apb_token', {app_token!r});
        }} catch (_) {{}}
        window.location.href = '/dashboard';
        </script><p>Login successful. Redirecting…</p></body></html>
        """
        return Response(content=html, media_type="text/html")

    @app.post("/api/auth/google", response_model=AuthResponse)
    async def auth_google(payload: GoogleAuthRequest) -> AuthResponse:
        google_user = await verify_google_id_token(payload.id_token)
        user_id = ensure_user_for_google(google_user["email"], google_user.get("name"), google_user.get("avatar_url"))
        token = create_session_for_user(user_id)
        return AuthResponse(access_token=token)

    @app.post("/api/auth/google/access-token", response_model=AuthResponse)
    async def auth_google_access_token(payload: GoogleAccessTokenRequest) -> AuthResponse:
        google_user = await verify_google_access_token(payload.access_token)
        user_id = ensure_user_for_google(google_user["email"], google_user.get("name"), google_user.get("avatar_url"))
        token = create_session_for_user(user_id)
        return AuthResponse(access_token=token)

    @app.get("/api/auth/github/start", response_model=GitHubAuthStartResponse)
    async def auth_github_start(request: Request) -> GitHubAuthStartResponse:
        client_id = get_github_client_id()
        if not client_id:
            return GitHubAuthStartResponse(enabled=False, auth_url=None)

        state = secrets.token_urlsafe(24)
        GITHUB_OAUTH_STATES[state] = time.time() + 600
        for key, expires in list(GITHUB_OAUTH_STATES.items()):
            if expires < time.time():
                GITHUB_OAUTH_STATES.pop(key, None)

        redirect_uri = str(request.base_url).rstrip("/") + "/api/auth/github/callback"
        auth_url = (
            "https://github.com/login/oauth/authorize"
            f"?client_id={client_id}&scope=read:user%20user:email&state={state}&redirect_uri={redirect_uri}"
        )
        return GitHubAuthStartResponse(enabled=True, auth_url=auth_url)

    @app.get("/api/auth/github/callback", include_in_schema=False)
    async def auth_github_callback(code: str | None = None, state: str | None = None) -> Response:
        if not code or not state:
            return Response(content="GitHub login failed: missing code/state.", media_type="text/plain", status_code=400)
        expires = GITHUB_OAUTH_STATES.pop(state, None)
        if not expires or expires < time.time():
            return Response(content="GitHub login failed: invalid or expired state.", media_type="text/plain", status_code=400)

        try:
            access_token = await exchange_github_code(code)
            gh_user = await fetch_github_identity(access_token)
            user_id = ensure_user_for_google(gh_user["email"], gh_user.get("name"), gh_user.get("avatar_url"))
            app_token = create_session_for_user(user_id)
        except HTTPException as exc:
            return Response(content=f"GitHub login failed: {exc.detail}", media_type="text/plain", status_code=400)

        html = f"""
        <!doctype html><html><body><script>
        try {{
          localStorage.removeItem('apb_token');
          sessionStorage.setItem('apb_token', {app_token!r});
        }} catch (_) {{}}
        window.location.href = '/dashboard';
        </script><p>Login successful. Redirecting…</p></body></html>
        """
        return Response(content=html, media_type="text/html")

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

    @app.get("/api/admin/stats", response_model=AdminStatsResponse)
    async def admin_stats(_: dict = Depends(require_admin)) -> AdminStatsResponse:
        return get_admin_stats()

    @app.get("/api/admin/users", response_model=AdminUsersResponse)
    async def admin_users(
        _: dict = Depends(require_admin),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        q: str | None = Query(default=None),
        sort_by: str = Query(default="created_at"),
        sort_dir: str = Query(default="desc"),
    ) -> AdminUsersResponse:
        return get_admin_users_overview(page=page, page_size=page_size, query=q, sort_by=sort_by, sort_dir=sort_dir)

    @app.get("/api/admin/resumes", response_model=AdminResumesResponse)
    async def admin_resumes(
        _: dict = Depends(require_admin),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        q: str | None = Query(default=None),
        sort_by: str = Query(default="updated_at"),
        sort_dir: str = Query(default="desc"),
    ) -> AdminResumesResponse:
        return get_admin_resumes_overview(page=page, page_size=page_size, query=q, sort_by=sort_by, sort_dir=sort_dir)

    @app.get("/api/admin/activity", response_model=AdminActivityResponse)
    async def admin_activity(
        _: dict = Depends(require_admin),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        action: str | None = Query(default=None),
        target_type: str | None = Query(default=None),
        admin_user_id: int | None = Query(default=None, ge=1),
        sort_by: str = Query(default="created_at"),
        sort_dir: str = Query(default="desc"),
    ) -> AdminActivityResponse:
        return get_admin_activity(
            page=page,
            page_size=page_size,
            action=action,
            target_type=target_type,
            admin_user_id=admin_user_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    @app.get("/api/admin/export/users.csv")
    async def admin_export_users_csv(
        _: dict = Depends(require_admin),
        q: str | None = Query(default=None),
        sort_by: str = Query(default="created_at"),
        sort_dir: str = Query(default="desc"),
    ) -> Response:
        csv_data = export_admin_users_csv(query=q, sort_by=sort_by, sort_dir=sort_dir)
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="admin-users.csv"'})

    @app.get("/api/admin/export/resumes.csv")
    async def admin_export_resumes_csv(
        _: dict = Depends(require_admin),
        q: str | None = Query(default=None),
        sort_by: str = Query(default="updated_at"),
        sort_dir: str = Query(default="desc"),
    ) -> Response:
        csv_data = export_admin_resumes_csv(query=q, sort_by=sort_by, sort_dir=sort_dir)
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="admin-resumes.csv"'})

    @app.get("/api/admin/export/activity.csv")
    async def admin_export_activity_csv(
        _: dict = Depends(require_admin),
        action: str | None = Query(default=None),
        target_type: str | None = Query(default=None),
        admin_user_id: int | None = Query(default=None, ge=1),
        sort_by: str = Query(default="created_at"),
        sort_dir: str = Query(default="desc"),
    ) -> Response:
        csv_data = export_admin_activity_csv(
            action=action,
            target_type=target_type,
            admin_user_id=admin_user_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="admin-activity.csv"'})

    @app.post("/api/admin/resumes/{resume_id}/publish", response_model=AdminActionResponse)
    async def admin_publish_resume(resume_id: int, admin: dict = Depends(require_admin)) -> AdminActionResponse:
        return force_publish_resume(admin["id"], resume_id)

    @app.delete("/api/admin/resumes/{resume_id}", response_model=AdminActionResponse)
    async def admin_delete_resume(resume_id: int, admin: dict = Depends(require_admin)) -> AdminActionResponse:
        return delete_resume_admin(admin["id"], resume_id)

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
        _: dict = Depends(get_current_user),
        github_service: GitHubService = Depends(get_github_service),
        linkedin_service: LinkedInService = Depends(get_linkedin_service),
    ) -> ProfileResponse:
        normalized_username = normalize_github_username(payload.username)
        logger.info("profile_request github=%s linkedin=%s", normalized_username, payload.linkedin_username)
        github_payload = await github_service.fetch_profile(normalized_username)
        linkedin_input = (payload.linkedin_username or "").strip()
        if not linkedin_input:
            linkedin_payload = LinkedInProfile(
                username=github_payload.profile.username,
                url="",
                summary=["GitHub-only mode enabled. Add LinkedIn username for additional enrichment."],
                provider_used="github_only",
                confidence_score=0.2,
                signals=["github_only"],
            )
        else:
            try:
                linkedin_payload = await linkedin_service.fetch_public_profile(linkedin_input)
                if "not_found" in (linkedin_payload.signals or []):
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LinkedIn username not found.")
            except HTTPException:
                raise
            except Exception:
                logger.exception("linkedin_enrichment_failed linkedin=%s", linkedin_input)
                linkedin_slug = linkedin_input.strip().strip("/").split("/")[-1].replace("in/", "")
                linkedin_payload = LinkedInProfile(
                    username=linkedin_slug or github_payload.profile.username,
                    url=f"https://www.linkedin.com/in/{linkedin_slug or github_payload.profile.username}/",
                    summary=["LinkedIn enrichment temporarily unavailable. GitHub-only mode applied."],
                    provider_used="endpoint_fallback",
                    confidence_score=0.05,
                    signals=["endpoint_fallback"],
                )
        return ProfileResponse(profile=github_payload.profile, repos=github_payload.repos, linkedin=linkedin_payload)

    @app.post("/api/generate", response_model=PortfolioResponse)
    async def generate(payload: GenerateRequest, user: dict = Depends(get_current_user)) -> PortfolioResponse:
        logger.info("generate_request github=%s variant=%s", payload.profile.username, payload.variant_id)
        try:
            result = generate_portfolio(payload)
        except Exception as exc:
            logger.exception("generate_failed github=%s", payload.profile.username)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Portfolio generation failed. Please try again.") from exc
        add_generation_history(user["id"], payload.profile.username, payload.variant_id, "auto")
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
