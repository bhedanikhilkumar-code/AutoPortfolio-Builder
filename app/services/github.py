from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx
from fastapi import HTTPException, status

from app.schemas import GitHubProfile, ProfileResponse, RepoSummary


GITHUB_API_BASE = "https://api.github.com"


@dataclass(slots=True)
class GitHubService:
    timeout_seconds: float = 10.0
    github_token: str | None = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))

    async def fetch_profile(self, username: str) -> ProfileResponse:
        try:
            user_response, repo_response = await self._fetch_profile_payload(
                username,
                headers=self._build_headers(include_token=True),
            )
        except HTTPException as exc:
            if self.github_token and exc.status_code == status.HTTP_502_BAD_GATEWAY:
                user_response, repo_response = await self._fetch_profile_payload(
                    username,
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
        return ProfileResponse(profile=profile, repos=repos)

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
