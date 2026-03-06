from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from app.schemas import GitHubProfile, ProfileResponse, RepoSummary


GITHUB_API_BASE = "https://api.github.com"
GITHUB_HOSTS = {"github.com", "www.github.com"}
GITHUB_USERNAME_RE = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$"
GITHUB_RESERVED_PATHS = {
    "about",
    "collections",
    "contact",
    "events",
    "explore",
    "features",
    "issues",
    "join",
    "login",
    "marketplace",
    "new",
    "notifications",
    "orgs",
    "pricing",
    "pulls",
    "search",
    "settings",
    "sponsors",
    "topics",
    "trending",
    "users",
}


@dataclass(slots=True)
class GitHubService:
    timeout_seconds: float = 10.0
    cache_ttl_seconds: int = 600
    github_token: str | None = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    _cache: dict[str, tuple[float, ProfileResponse]] = field(default_factory=dict)

    async def fetch_profile(self, username: str) -> ProfileResponse:
        canonical_username = normalize_github_username(username)
        cache_key = canonical_username.lower()
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        try:
            user_response, repo_response = await self._fetch_profile_payload(
                canonical_username,
                headers=self._build_headers(include_token=True),
            )
        except HTTPException as exc:
            if self.github_token and exc.status_code == status.HTTP_502_BAD_GATEWAY:
                user_response, repo_response = await self._fetch_profile_payload(
                    canonical_username,
                    headers=self._build_headers(include_token=False),
                )
            else:
                raise

        profile = GitHubProfile(
            username=user_response["login"],
            name=user_response.get("name"),
            bio=user_response.get("bio"),
            avatar_url=user_response.get("avatar_url"),
            html_url=user_response["html_url"],
            blog=user_response.get("blog"),
            location=user_response.get("location"),
            email=user_response.get("email"),
            public_repos=user_response.get("public_repos", 0),
            followers=user_response.get("followers", 0),
            following=user_response.get("following", 0),
        )
        repos = [
            RepoSummary(
                name=repo["name"],
                description=repo.get("description"),
                html_url=repo["html_url"],
                homepage=repo.get("homepage"),
                stargazers_count=repo.get("stargazers_count", 0),
                forks_count=repo.get("forks_count", 0),
                language=repo.get("language"),
                topics=repo.get("topics") or [],
                updated_at=repo.get("updated_at"),
            )
            for repo in repo_response
            if not repo.get("fork", False)
        ]
        response = ProfileResponse(profile=profile, repos=repos)
        self._cache[cache_key] = (now, response)
        return response

    async def _fetch_profile_payload(
        self,
        username: str,
        headers: dict[str, str],
    ) -> tuple[dict, list]:
        async with httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers=headers,
            timeout=self.timeout_seconds,
        ) as client:
            user_response = await self._get(client, f"/users/{username}")
            repo_response = await self._get(
                client,
                f"/users/{username}/repos",
                params={
                    "sort": "updated",
                    "per_page": 100,
                    "type": "owner",
                },
            )
        return user_response, repo_response

    def _build_headers(self, *, include_token: bool = True) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AutoPortfolio-Builder",
        }
        if include_token and self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> dict | list:
        try:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="GitHub user not found.",
                ) from exc
            if exc.response.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "GitHub API rate limited or unavailable. "
                        "Set GITHUB_TOKEN to increase the rate limit."
                    ),
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="GitHub API request failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to reach GitHub API.",
            ) from exc


def normalize_github_username(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub username is required.")

    candidate = raw
    if candidate.startswith("@"):
        candidate = candidate[1:]

    if "github.com" in candidate.lower() or candidate.lower().startswith("http://") or candidate.lower().startswith("https://"):
        if "://" not in candidate:
            candidate = f"https://{candidate}"
        parsed = urlparse(candidate)
        host = parsed.netloc.lower()
        if host not in GITHUB_HOSTS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid GitHub profile URL.")
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid GitHub username.")
        candidate = path_parts[0]

    candidate = candidate.strip("/")
    if not candidate:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid GitHub username.")

    if candidate.lower() in GITHUB_RESERVED_PATHS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid GitHub profile URL.")

    if not re.fullmatch(GITHUB_USERNAME_RE, candidate):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid GitHub username.")
    return candidate
