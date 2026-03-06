from __future__ import annotations

from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app, get_github_service, get_linkedin_service
from app.schemas import GenerateRequest, GitHubProfile, LinkedInProfile, ProfileResponse, RepoSummary
from app.services.github import GitHubService, normalize_github_username
from app.services.portfolio import generate_portfolio


class StubGitHubService:
    async def fetch_profile(self, username: str) -> ProfileResponse:
        return ProfileResponse(
            profile=GitHubProfile(
                username=username,
                name="Ada Lovelace",
                bio="Builds analytical engines.",
                avatar_url="https://example.com/avatar.png",
                html_url=f"https://github.com/{username}",
                blog="https://example.dev",
                location="London",
                email="ada@example.dev",
                public_repos=2,
                followers=10,
                following=3,
            ),
            repos=[
                RepoSummary(
                    name="engine",
                    description="Computing engine experiments",
                    html_url="https://github.com/octocat/engine",
                    homepage="https://engine.example.dev",
                    stargazers_count=42,
                    forks_count=7,
                    language="Python",
                    topics=["automation", "analysis"],
                    updated_at="2026-02-28T00:00:00Z",
                ),
                RepoSummary(
                    name="notes",
                    description="Technical notes",
                    html_url="https://github.com/octocat/notes",
                    stargazers_count=10,
                    forks_count=1,
                    language="Markdown",
                    topics=["writing"],
                    updated_at="2026-02-27T00:00:00Z",
                ),
            ],
            linkedin=LinkedInProfile(
                username="octocat",
                url="https://www.linkedin.com/in/octocat/",
                title="Ada Lovelace",
                headline="Software Engineer",
                summary=["Software Engineer", "Public profile connected."],
            ),
        )


class StubLinkedInService:
    async def fetch_public_profile(self, username: str) -> LinkedInProfile:
        return LinkedInProfile(
            username=username,
            url=f"https://www.linkedin.com/in/{username}/",
            title="Ada Lovelace",
            headline="Software Engineer",
            summary=["Software Engineer", "Public profile connected."],
        )


class FailingGitHubService:
    async def fetch_profile(self, username: str) -> ProfileResponse:
        raise HTTPException(status_code=404, detail="GitHub user not found.")


class SlugInferenceLinkedInService:
    async def fetch_public_profile(self, username: str) -> LinkedInProfile:
        return LinkedInProfile(
            username=username,
            url=f"https://www.linkedin.com/in/{username}/",
            provider_used="slug_inference",
            confidence_score=0.25,
            signals=["slug_inference"],
            summary=["LinkedIn profile inferred from username."],
        )


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides[get_github_service] = lambda: StubGitHubService()
    app.dependency_overrides[get_linkedin_service] = lambda: StubLinkedInService()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def make_auth_headers(name: str = "Test User") -> dict[str, str]:
    email = f"tester-{uuid4().hex[:8]}@testmail.com"
    register = client.post("/api/auth/register", json={"name": name, "email": email, "password": "StrongPass@123"})
    assert register.status_code == 200
    token = register.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_google_auth_config_endpoint() -> None:
    response = client.get("/api/auth/google/config")

    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload


def test_logout_revokes_session() -> None:
    email = f"logout-{uuid4().hex[:8]}@testmail.com"
    register = client.post("/api/auth/register", json={"name": "Logout User", "email": email, "password": "StrongPass@123"})
    token = register.json()["access_token"]

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200

    dashboard = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert dashboard.status_code == 401


def test_admin_endpoint_requires_auth() -> None:
    response = client.get("/api/admin/stats", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def test_non_admin_forbidden_for_admin_endpoint() -> None:
    normal_email = f"normal-{uuid4().hex[:8]}@testmail.com"
    register = client.post(
        "/api/auth/register",
        json={"name": "Normal User", "email": normal_email, "password": "StrongPass@123"},
    )
    token = register.json()["access_token"]

    response = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_endpoints_and_actions(monkeypatch) -> None:
    admin_email = f"admin-{uuid4().hex[:8]}@testmail.com"
    target_email = f"target-{uuid4().hex[:8]}@testmail.com"
    monkeypatch.setenv("ADMIN_EMAILS", admin_email)

    admin_register = client.post(
        "/api/auth/register",
        json={"name": "Admin User", "email": admin_email, "password": "StrongPass@123"},
    )
    assert admin_register.status_code == 200
    admin_token = admin_register.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_register = client.post(
        "/api/auth/register",
        json={"name": "Target User", "email": target_email, "password": "StrongPass@123"},
    )
    assert user_register.status_code == 200
    user_token = user_register.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    users_before = client.get("/api/admin/users", headers=admin_headers).json()["users"]
    target_user = next(u for u in users_before if u["email"] == target_email)
    assert target_user["email"] == target_email

    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=user_headers).json()
    portfolio = client.post("/api/generate", json=profile_payload, headers=user_headers).json()
    save = client.post(
        "/api/dashboard/resumes",
        headers=user_headers,
        json={"title": "Target CV", "portfolio": portfolio, "status": "draft"},
    )
    assert save.status_code == 200
    resume_id = save.json()["resume_id"]

    publish = client.post(f"/api/admin/resumes/{resume_id}/publish", headers=admin_headers)
    assert publish.status_code == 200

    delete = client.delete(f"/api/admin/resumes/{resume_id}", headers=admin_headers)
    assert delete.status_code == 200

    activity = client.get("/api/admin/activity", headers=admin_headers)
    assert activity.status_code == 200
    assert len(activity.json()["logs"]) >= 2

    users_csv = client.get("/api/admin/export/users.csv", headers=admin_headers)
    assert users_csv.status_code == 200
    assert "text/csv" in users_csv.headers.get("content-type", "")


def test_profile_endpoint_returns_profile_and_repos() -> None:
    headers = make_auth_headers()
    response = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["username"] == "octocat"
    assert payload["linkedin"]["url"].endswith("/octocat/")
    assert len(payload["repos"]) == 2
    assert payload["repos"][0]["name"] == "engine"


def test_profile_endpoint_supports_github_profile_url_and_optional_linkedin() -> None:
    headers = make_auth_headers()
    response = client.post("/api/profile", json={"username": "https://github.com/octocat/"}, headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["username"] == "octocat"
    assert payload["linkedin"]["provider_used"] == "github_only"


def test_generate_endpoint_builds_portfolio_sections() -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()

    response = client.post("/api/generate", json=profile_payload, headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"theme", "hero", "about", "projects", "skills", "contact"}
    assert payload["theme"] == "modern"
    assert payload["hero"]["content"]["headline"] == "Ada Lovelace builds software that ships."
    assert payload["projects"]["content"]["items"][0]["name"] == "engine"
    assert "Python" in payload["skills"]["content"]["highlighted"]


def test_profile_endpoint_validates_username() -> None:
    headers = make_auth_headers()
    response = client.post("/api/profile", json={"username": "not valid", "linkedin_username": "octocat"}, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_profile_endpoint_validates_linkedin_username() -> None:
    headers = make_auth_headers()
    response = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "bad user"}, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_profile_endpoint_allows_slug_inference_fallback() -> None:
    headers = make_auth_headers()
    app.dependency_overrides[get_linkedin_service] = lambda: SlugInferenceLinkedInService()

    response = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "randomslug"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["linkedin"]["provider_used"] == "slug_inference"


def test_generate_endpoint_accepts_selected_theme() -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()

    response = client.post("/api/generate", json={**profile_payload, "theme": "minimal"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["theme"] == "minimal"


def test_profile_endpoint_returns_consistent_error_payload() -> None:
    headers = make_auth_headers()
    app.dependency_overrides[get_github_service] = lambda: FailingGitHubService()

    response = client.post("/api/profile", json={"username": "ghost", "linkedin_username": "ghost"}, headers=headers)

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "GitHub user not found.",
        }
    }


def test_github_service_reads_token_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")

    service = GitHubService()

    assert service._build_headers()["Authorization"] == "Bearer secret-token"


def test_normalize_github_username_accepts_profile_and_repo_urls() -> None:
    assert normalize_github_username("https://github.com/octocat") == "octocat"
    assert normalize_github_username("https://github.com/octocat/hello-world?tab=readme") == "octocat"
    assert normalize_github_username("@octocat") == "octocat"


def test_normalize_github_username_rejects_non_profile_url() -> None:
    try:
        normalize_github_username("https://github.com/features")
    except HTTPException as exc:
        assert exc.status_code == 422
        assert "valid GitHub" in str(exc.detail)
    else:
        assert False, "Expected HTTPException for reserved GitHub path."


def test_github_service_skips_authorization_without_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    service = GitHubService()

    assert "Authorization" not in service._build_headers()


def test_generate_endpoint_handles_empty_repositories() -> None:
    headers = make_auth_headers()
    payload = {
        "profile": {
            "username": "solo",
            "name": None,
            "bio": None,
            "avatar_url": None,
            "html_url": "https://github.com/solo",
            "blog": None,
            "location": None,
            "email": None,
            "public_repos": 0,
            "followers": 0,
            "following": 0,
        },
        "repos": [],
        "linkedin": {
            "username": "solo",
            "url": "https://www.linkedin.com/in/solo/",
            "title": None,
            "headline": None,
            "summary": ["Public profile connected."],
        },
        "theme": "modern",
    }

    response = client.post("/api/generate", json=payload, headers=headers)

    assert response.status_code == 200
    portfolio = response.json()
    assert portfolio["hero"]["content"]["headline"] == "solo builds software that ships."
    assert "Getting started with open source projects on GitHub" in portfolio["about"]["content"]["summary"]
    assert portfolio["projects"]["content"]["items"] == []
    assert portfolio["skills"]["content"]["highlighted"] == []


def test_generate_portfolio_uses_topics_when_languages_are_missing() -> None:
    portfolio = generate_portfolio(
        GenerateRequest(
            profile=GitHubProfile(
                username="builder",
                name="Builder",
                bio=None,
                avatar_url=None,
                html_url="https://github.com/builder",
                blog=None,
                location=None,
                email=None,
                public_repos=1,
                followers=0,
                following=0,
            ),
            repos=[
                RepoSummary(
                    name="toolkit",
                    description=None,
                    html_url="https://github.com/builder/toolkit",
                    language=None,
                    topics=["cli", "automation", "cli"],
                )
            ],
            linkedin=LinkedInProfile(
                username="builder",
                url="https://www.linkedin.com/in/builder/",
                summary=["Engineering"],
            ),
        )
    )

    assert portfolio.skills.content["languages"] == []
    assert portfolio.skills.content["highlighted"][:2] == ["cli", "automation"]


def test_export_html_endpoint_returns_downloadable_file() -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()
    portfolio_payload = client.post("/api/generate", json=profile_payload, headers=headers).json()
    portfolio_payload["hero"]["content"]["headline"] = "Custom export headline"

    response = client.post(
        "/api/export/html",
        json={"portfolio": portfolio_payload, "filename": "ada-portfolio"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["content-disposition"] == 'attachment; filename="ada-portfolio.html"'
    assert "Custom export headline" in response.text
    assert "<!DOCTYPE html>" in response.text


def test_export_zip_endpoint_returns_archive_with_expected_files() -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()
    portfolio_payload = client.post("/api/generate", json=profile_payload, headers=headers).json()

    response = client.post("/api/export/zip", json={"portfolio": portfolio_payload})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    archive = ZipFile(BytesIO(response.content))

    assert sorted(archive.namelist()) == ["index.html", "portfolio.json"]
    assert "Ada Lovelace builds software that ships." in archive.read("index.html").decode("utf-8")
    assert '"theme": "modern"' in archive.read("portfolio.json").decode("utf-8")


def test_export_pdf_endpoint_returns_downloadable_file() -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()
    portfolio_payload = client.post("/api/generate", json=profile_payload, headers=headers).json()

    response = client.post(
        "/api/export/pdf",
        json={"portfolio": portfolio_payload, "filename": "ada-portfolio"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="ada-portfolio.pdf"'
    assert response.content.startswith(b"%PDF")


def test_share_endpoint_returns_resume_link(monkeypatch) -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()
    portfolio_payload = client.post("/api/generate", json=profile_payload, headers=headers).json()

    async def no_shortener(_: str) -> str | None:
        return None

    monkeypatch.setattr("app.main._shorten_url", no_shortener)

    response = client.post(
        "/api/share",
        json={"portfolio": portfolio_payload, "filename": "ada-portfolio", "use_short_link": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["share_id"]
    assert payload["resume_url"].endswith(f"/resume/{payload['share_id']}")
    assert payload["share_url"] == payload["resume_url"]


def test_shared_resume_endpoint_renders_portfolio(monkeypatch) -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()
    portfolio_payload = client.post("/api/generate", json=profile_payload, headers=headers).json()

    async def no_shortener(_: str) -> str | None:
        return None

    monkeypatch.setattr("app.main._shorten_url", no_shortener)

    share_response = client.post("/api/share", json={"portfolio": portfolio_payload})
    share_id = share_response.json()["share_id"]

    response = client.get(f"/resume/{share_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Ada Lovelace builds software that ships." in response.text


def test_export_endpoint_validates_filename() -> None:
    headers = make_auth_headers()
    profile_payload = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers).json()
    portfolio_payload = client.post("/api/generate", json=profile_payload, headers=headers).json()

    response = client.post(
        "/api/export/html",
        json={"portfolio": portfolio_payload, "filename": "invalid file"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_full_profile_generate_edit_export_flow() -> None:
    headers = make_auth_headers()
    profile_response = client.post("/api/profile", json={"username": "octocat", "linkedin_username": "octocat"}, headers=headers)
    assert profile_response.status_code == 200

    generated_response = client.post("/api/generate", json={**profile_response.json(), "theme": "minimal"}, headers=headers)
    assert generated_response.status_code == 200

    edited_portfolio = generated_response.json()
    edited_portfolio["about"]["content"]["name"] = "Ada Lovelace, FRS"
    edited_portfolio["contact"]["content"]["email"] = "hello@example.dev"

    export_response = client.post("/api/export/html", json={"portfolio": edited_portfolio})

    assert export_response.status_code == 200
    assert export_response.headers["content-disposition"] == 'attachment; filename="ada-lovelace-frs.html"'
    assert "Ada Lovelace, FRS" in export_response.text
    assert "hello@example.dev" in export_response.text




