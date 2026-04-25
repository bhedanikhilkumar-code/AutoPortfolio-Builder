from __future__ import annotations

from pathlib import Path
import base64
import logging
import os
import secrets
import time

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile, status
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
    AvatarResponse,
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
    VerificationRequest,
    VerificationResponse,
    VerificationStatusResponse,
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
from app.auth.service import (
    create_email_verification_token,
    create_session,
    create_session_for_user,
    ensure_user_for_google,
    register_user,
    resolve_user_from_token,
    revoke_session,
    set_custom_avatar,
    verify_email_token,
)
from app.branding.service import get_branding, upsert_branding
from app.core.db import init_db
from app.dashboard.service import add_generation_history, build_dashboard, save_resume_snapshot
from app.deploy_export.service import build_deploy_package
from app.resume_versions.service import list_versions, restore_version
from app.services.github import GitHubService, normalize_github_username
from app.services.linkedin import LinkedInService
from app.services.input_validation import normalize_linkedin_input, validate_manual_inputs
from app.services.portfolio import (
    build_export_filename,
    build_portfolio_zip,
    generate_portfolio,
    render_portfolio_pdf,
    render_portfolio_html,
)
from app.deploy_export.service import (
    build_deploy_package,
    export_portfolio_markdown,
    export_portfolio_json,
    export_portfolio_latex,
)
from app.ats_analyzer.service import analyze_ats_score, get_role_recommendations
from app.api_keys.service import (
    check_rate_limit,
    create_api_key,
    list_api_keys,
    revoke_api_key,
    validate_api_key,
    init_api_keys_db,
    hash_api_key,
)
from app.webhooks.service import (
    create_webhook,
    list_webhooks,
    delete_webhook,
    trigger_webhook,
    WEBHOOK_EVENTS,
)
from app.themes.service import (
    THEMES,
    get_theme,
    list_themes,
    generate_custom_css,
    inject_theme,
)
from app.seo.service import (
    analyze_seo_score,
    inject_seo_tags,
    generate_meta_tags,
    generate_opengraph_tags,
    generate_twitter_card,
    generate_jsonld,
)
from app.preview.service import (
    get_preview_html,
    get_multi_theme_preview,
)
from app.schemas import (
    SEOAnalysisRequest,
    SEOAnalysisResponse,
    SEOMetaResponse,
    PreviewRequest,
    PreviewResponse,
    MultiThemePreviewRequest,
    MultiThemePreviewResponse,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SHARED_PORTFOLIOS: dict[str, PortfolioResponse] = {}
GITHUB_OAUTH_STATES: dict[str, float] = {}
GOOGLE_OAUTH_STATES: dict[str, float] = {}
logger = logging.getLogger("autoporfolio_builder")
MAX_AVATAR_BYTES = 2 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _detect_avatar_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "webp"
    return None


def _serialize_avatar(user: dict) -> AvatarResponse:
    return AvatarResponse(
        avatar_url=user.get("avatar_url"),
        social_avatar_url=user.get("social_avatar_url"),
        custom_avatar_url=user.get("custom_avatar_url"),
    )


def _send_verification_email(email: str, token: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_from = os.getenv("SMTP_FROM", smtp_user).strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    if not smtp_host or not smtp_from:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email service not configured.")

    verify_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if not verify_url:
        verify_url = "http://localhost:8000"
    verify_url = f"{verify_url}/api/auth/verify-email?token={token}"

    from email.message import EmailMessage
    import smtplib

    message = EmailMessage()
    message["Subject"] = "Verify your AutoPortfolio account"
    message["From"] = smtp_from
    message["To"] = email
    message.set_content(
        "Welcome to AutoPortfolio Builder!\n\n"
        f"Please verify your email by clicking this link:\n{verify_url}\n\n"
        "This link expires in 24 hours."
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_pass)
            server.send_message(message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to send verification email.") from exc


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


def require_verified_user(user: dict = Depends(get_current_user)) -> dict:
    if not bool(user.get("email_verified", False)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before continuing.")
    return user


def _google_redirect_uri(request: Request) -> str:
    configured = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
    if configured:
        return configured
    return str(request.base_url).rstrip("/") + "/api/auth/google/callback"


def create_app() -> FastAPI:
    init_db()
    init_api_keys_db()
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
        user_id = register_user(payload.name, payload.email, payload.password)
        token, _ = create_session(payload.email, payload.password)
        verify_token, verify_email, already_verified = create_email_verification_token(user_id)
        message = "Please verify your email before continuing."
        if not already_verified and verify_token:
            try:
                _send_verification_email(verify_email, verify_token)
                message = "Verification email sent. Please verify your email before continuing."
            except HTTPException as exc:
                logger.warning("verification_email_send_failed register email=%s detail=%s", verify_email, exc.detail)
                message = "Account created. Verification email could not be sent right now. Please use resend verification."
        return AuthResponse(access_token=token, email_verified=False, message=message)

    @app.post("/api/auth/login", response_model=AuthResponse)
    async def auth_login(payload: LoginRequest) -> AuthResponse:
        token, _ = create_session(payload.email, payload.password)
        user = resolve_user_from_token(token)
        if not bool(user.get("email_verified", False)):
            return AuthResponse(access_token=token, email_verified=False, message="Please verify your email before continuing.")
        return AuthResponse(access_token=token, email_verified=True)

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
          localStorage.setItem('apb_token', {app_token!r});
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
        return AuthResponse(access_token=token, email_verified=True)

    @app.post("/api/auth/verification/resend", response_model=VerificationResponse)
    async def resend_verification(payload: VerificationRequest) -> VerificationResponse:
        email = (payload.email or "").strip().lower()
        if not email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required.")
        from app.core.db import get_connection

        conn = get_connection()
        try:
            row = conn.execute("SELECT id, email_verified FROM users WHERE email = ?", (email,)).fetchone()
        finally:
            conn.close()

        if not row:
            return VerificationResponse(ok=True, message="If this email exists, a verification link has been sent.")
        if bool(int(row["email_verified"])):
            return VerificationResponse(ok=True, message="Email already verified.")

        token, target_email, _ = create_email_verification_token(int(row["id"]))
        try:
            _send_verification_email(target_email, token)
            return VerificationResponse(ok=True, message="Verification email sent successfully.")
        except HTTPException as exc:
            logger.warning("verification_email_send_failed resend email=%s detail=%s", target_email, exc.detail)
            return VerificationResponse(ok=False, message="Failed to send verification email.")

    @app.post("/api/auth/verification/status", response_model=VerificationStatusResponse)
    async def verification_status(payload: VerificationRequest) -> VerificationStatusResponse:
        email = (payload.email or "").strip().lower()
        if not email:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required.")
        from app.core.db import get_connection

        conn = get_connection()
        try:
            row = conn.execute("SELECT email_verified FROM users WHERE email = ?", (email,)).fetchone()
        finally:
            conn.close()

        return VerificationStatusResponse(email=email, email_verified=bool(int(row["email_verified"])) if row else False)

    @app.get("/api/auth/verify-email", include_in_schema=False)
    async def verify_email(token: str | None = None) -> Response:
        ok = verify_email_token(token or "")
        if ok:
            html = """<!doctype html><html><body><h3>Email verified successfully.</h3><p>You can return to login now.</p><script>setTimeout(()=>window.location.href='/login?verified=1',1200)</script></body></html>"""
            return Response(content=html, media_type="text/html")
        html = """<!doctype html><html><body><h3>Verification link is invalid or expired.</h3><p>Please request a new verification email.</p><script>setTimeout(()=>window.location.href='/login?verified=0',1600)</script></body></html>"""
        return Response(content=html, media_type="text/html", status_code=400)

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
          localStorage.setItem('apb_token', {app_token!r});
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

    @app.post("/api/account/avatar", response_model=AvatarResponse)
    async def upload_account_avatar(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> AvatarResponse:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Please choose an image file.")
        if len(data) > MAX_AVATAR_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image too large. Max size is 2MB.")

        detected = _detect_avatar_type(data)
        if detected not in ALLOWED_AVATAR_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid image format. Use JPG, JPEG, PNG, or WEBP.")

        mime = ALLOWED_AVATAR_TYPES[detected]
        encoded = base64.b64encode(data).decode("ascii")
        custom_avatar_url = f"data:{mime};base64,{encoded}"
        set_custom_avatar(user["id"], custom_avatar_url)
        updated_user = {**user, "custom_avatar_url": custom_avatar_url, "avatar_url": custom_avatar_url}
        return _serialize_avatar(updated_user)

    @app.delete("/api/account/avatar", response_model=AvatarResponse)
    async def remove_account_avatar(user: dict = Depends(get_current_user)) -> AvatarResponse:
        set_custom_avatar(user["id"], None)
        updated_user = {**user, "custom_avatar_url": None, "avatar_url": user.get("social_avatar_url")}
        return _serialize_avatar(updated_user)

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

    @app.post("/api/dashboard/resumes/{resume_id}/duplicate", response_model=SaveResumeResponse)
    async def duplicate_resume(resume_id: int, user: dict = Depends(get_current_user)) -> SaveResumeResponse:
        from app.core.db import get_connection

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT title, status, portfolio_json FROM resumes WHERE id = ? AND user_id = ?",
                (resume_id, user["id"]),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

            duplicate_title = f"{row['title']} (Copy)"
            cursor = conn.execute(
                "INSERT INTO resumes(user_id, title, status, portfolio_json) VALUES(?, ?, ?, ?)",
                (user["id"], duplicate_title, row["status"], row["portfolio_json"]),
            )
            new_resume_id = int(cursor.lastrowid)
            conn.execute(
                "INSERT INTO resume_versions(resume_id, version_number, portfolio_json) VALUES(?, ?, ?)",
                (new_resume_id, 1, row["portfolio_json"]),
            )
            conn.commit()
            return SaveResumeResponse(resume_id=new_resume_id, message="Resume duplicated successfully.")
        finally:
            conn.close()

    @app.delete("/api/dashboard/resumes/{resume_id}", response_model=SaveResumeResponse)
    async def delete_resume(resume_id: int, user: dict = Depends(get_current_user)) -> SaveResumeResponse:
        from app.core.db import get_connection

        conn = get_connection()
        try:
            row = conn.execute("SELECT id FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user["id"])).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

            conn.execute("DELETE FROM resume_versions WHERE resume_id = ?", (resume_id,))
            conn.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user["id"]))
            conn.commit()
            return SaveResumeResponse(resume_id=resume_id, message="Resume deleted successfully.")
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
            linkedin_slug = normalize_linkedin_input(linkedin_input)
            linkedin_payload = await linkedin_service.fetch_public_profile(linkedin_slug)
            if "not_found" in (linkedin_payload.signals or []):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LinkedIn username not found.")
            if linkedin_payload.provider_used in {"slug_inference", "global_fallback"} and linkedin_payload.confidence_score < 0.35:
                linkedin_payload.summary = [
                    "LinkedIn profile could not be fully validated right now; generation continued with low-confidence LinkedIn enrichment.",
                    *(linkedin_payload.summary or []),
                ][:4]
                linkedin_payload.signals = list(dict.fromkeys([*(linkedin_payload.signals or []), "low_confidence_accepted"]))
        return ProfileResponse(profile=github_payload.profile, repos=github_payload.repos, linkedin=linkedin_payload)

    @app.post("/api/generate", response_model=PortfolioResponse)
    async def generate(payload: GenerateRequest, user: dict = Depends(get_current_user)) -> PortfolioResponse:
        logger.info("generate_request github=%s variant=%s", payload.profile.username, payload.variant_id)
        if payload.manual_input:
            normalized_manual_github = normalize_github_username(payload.manual_input.github)
            if normalized_manual_github.lower() != payload.profile.username.lower():
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub input does not match fetched profile.")
            validate_manual_inputs(
                name=payload.manual_input.name,
                email=payload.manual_input.email,
                github=payload.manual_input.github,
                linkedin=payload.manual_input.linkedin,
                skills=payload.manual_input.skills,
                projects=payload.manual_input.projects,
            )
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

    # ====== NEW: ATS Analysis & Export Formats ======
    @app.post("/api/portfolio/analyze", response_model=ATSAnalysisResponse)
    async def analyze_portfolio_ats(payload: ATSAnalysisRequest) -> ATSAnalysisResponse:
        result = analyze_ats_score(payload.portfolio)
        return ATSAnalysisResponse(
            overall_score=int(result["overall_score"]),
            keyword_score=result["keyword_score"],
            format_score=result["format_score"],
            readability_score=result["readability_score"],
            completeness_score=result["completeness_score"],
            improvements=result["improvements"],
            missing_keywords=result["missing_keywords"],
            role_scores=result["role_scores"],
        )

    @app.post("/api/portfolio/recommend-role", response_model=RoleRecommendationResponse)
    async def recommend_role(payload: ATSAnalysisRequest) -> RoleRecommendationResponse:
        result = get_role_recommendations(payload.portfolio)
        return RoleRecommendationResponse(
            recommended_role=result["recommended_role"],
            role_scores=result["role_scores"],
        )

    @app.post("/api/portfolio/export", response_model=ExportFormatResponse)
    async def export_portfolio(payload: ExportFormatRequest) -> ExportFormatResponse:
        format_map = {
            "markdown": (export_portfolio_markdown, "text/markdown"),
            "json": (export_portfolio_json, "application/json"),
            "latex": (export_portfolio_latex, "application/x-tex"),
        }
        exporter, content_type = format_map.get(payload.format, (export_portfolio_json, "application/json"))
        content = exporter(payload.portfolio)
        return ExportFormatResponse(format=payload.format, content=content, content_type=content_type)

    # ====== NEW: API Keys ======
    @app.post("/api/keys", response_model=APIKeyResponse)
    async def create_api_key(payload: APIKeyCreateRequest, user: dict = Depends(get_current_user)) -> APIKeyResponse:
        key_id, key = create_api_key(user["id"], payload.name, payload.rate_limit)
        return APIKeyResponse(key_id=key_id, key=key, name=payload.name, rate_limit=payload.rate_limit)

    @app.get("/api/keys")
    async def get_api_keys(user: dict = Depends(get_current_user)):
        keys = list_api_keys(user["id"])
        return {"keys": keys}

    @app.delete("/api/keys/{key_id}")
    async def delete_api_key(key_id: str, user: dict = Depends(get_current_user)):
        revoke_api_key(key_id, user["id"])
        return {"ok": True, "message": "API key revoked"}

    # ====== NEW: Webhooks ======
    @app.post("/api/webhooks", response_model=WebhookResponse)
    async def create_webhook_endpoint(
        payload: WebhookRequest,
        user: dict = Depends(get_current_user),
    ) -> WebhookResponse:
        # Validate events
        valid_events = [e for e in payload.events if e in WEBHOOK_EVENTS]
        if not valid_events:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid events. Valid: {WEBHOOK_EVENTS}",
            )
        webhook_id, secret = create_webhook(user["id"], payload.url, valid_events, payload.name)
        return WebhookResponse(
            webhook_id=webhook_id,
            secret=secret,
            name=payload.name,
            url=payload.url,
            events=valid_events,
        )

    @app.get("/api/webhooks", response_model=WebhookListResponse)
    async def list_webhooks_endpoint(user: dict = Depends(get_current_user)) -> WebhookListResponse:
        webhooks = list_webhooks(user["id"])
        return WebhookListResponse(webhooks=webhooks)

    @app.delete("/api/webhooks/{webhook_id}")
    async def delete_webhook_endpoint(
        webhook_id: str,
        user: dict = Depends(get_current_user),
    ):
        delete_webhook(webhook_id, user["id"])
        return {"ok": True, "message": "Webhook deleted"}

    # ====== NEW: Themes ======
    @app.get("/api/themes", response_model=ThemeListResponse)
    async def get_themes() -> ThemeListResponse:
        themes = [
            ThemeInfo(
                id=k,
                name=v["name"],
                primary=v["primary"],
                secondary=v["secondary"],
                background=v["background"],
                text=v["text"],
                accent=v["accent"],
            )
            for k, v in THEMES.items()
        ]
        return ThemeListResponse(themes=themes)

    @app.post("/api/themes/css", response_model=ThemeCSSResponse)
    async def generate_theme_css(payload: ThemeCSSRequest) -> ThemeCSSResponse:
        css = generate_custom_css(payload.theme_id, payload.custom_css, payload.font_family)
        return ThemeCSSResponse(theme_id=payload.theme_id, css=css)

    # ====== SEO Optimization ======
    @app.post("/api/portfolio/seo/analyze", response_model=SEOAnalysisResponse)
    async def analyze_portfolio_seo(payload: SEOAnalysisRequest) -> SEOAnalysisResponse:
        result = analyze_seo_score(payload.portfolio)
        return SEOAnalysisResponse(
            score=result["score"],
            grade=result["grade"],
            improvements=result["improvements"],
        )

    @app.post("/api/portfolio/seo/meta", response_model=SEOMetaResponse)
    async def get_portfolio_seo_meta(payload: SEOAnalysisRequest) -> SEOMetaResponse:
        meta = generate_meta_tags(payload.portfolio)
        return SEOMetaResponse(
            title=meta["title"],
            description=meta["description"],
            keywords=meta["keywords"],
            og_tags=generate_opengraph_tags(payload.portfolio),
            twitter_tags=generate_twitter_card(payload.portfolio),
            jsonld=generate_jsonld(payload.portfolio),
        )

    # ====== Live Preview ======
    @app.post("/api/portfolio/preview", response_model=PreviewResponse)
    async def generate_preview(payload: PreviewRequest) -> PreviewResponse:
        html = get_preview_html(
            payload.portfolio,
            payload.theme_id,
            payload.inject_seo,
        )
        return PreviewResponse(html=html)

    @app.post("/api/portfolio/preview/themes", response_model=MultiThemePreviewResponse)
    async def generate_multi_theme_preview(payload: MultiThemePreviewRequest) -> MultiThemePreviewResponse:
        previews = get_multi_theme_preview(
            payload.portfolio,
            payload.theme_ids,
        )
        return MultiThemePreviewResponse(previews=previews)

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
