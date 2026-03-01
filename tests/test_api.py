from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, get_github_service
from app.schemas import GitHubProfile, ProfileResponse, RepoSummary


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
        )


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides[get_github_service] = lambda: StubGitHubService()


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_profile_endpoint_returns_profile_and_repos() -> None:
    response = client.post("/api/profile", json={"username": "octocat"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["username"] == "octocat"
    assert len(payload["repos"]) == 2
    assert payload["repos"][0]["name"] == "engine"


def test_generate_endpoint_builds_portfolio_sections() -> None:
    profile_payload = client.post("/api/profile", json={"username": "octocat"}).json()

    response = client.post("/api/generate", json=profile_payload)

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"hero", "about", "projects", "skills", "contact"}
    assert payload["hero"]["content"]["headline"] == "Ada Lovelace builds software that ships."
    assert payload["projects"]["content"]["items"][0]["name"] == "engine"
    assert "Python" in payload["skills"]["content"]["highlighted"]


def test_profile_endpoint_validates_username() -> None:
    response = client.post("/api/profile", json={"username": "not valid"})

    assert response.status_code == 422
