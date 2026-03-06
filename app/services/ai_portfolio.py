from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import httpx

from app.schemas import GitHubProfile, RepoSummary


@dataclass(slots=True)
class AIPortfolioService:
    api_key: str = field(default_factory=lambda: os.getenv("AI_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip())
    base_url: str = field(default_factory=lambda: os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/"))
    model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini")
    timeout_seconds: float = 20.0

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_content(
        self,
        profile: GitHubProfile,
        repos: list[RepoSummary],
        top_languages: list[str],
        top_topics: list[str],
    ) -> dict | None:
        if not self.is_configured():
            return None

        profile_blob = {
            "username": profile.username,
            "name": profile.name,
            "bio": profile.bio,
            "location": profile.location,
            "public_repos": profile.public_repos,
        }
        repos_blob = [
            {
                "name": repo.name,
                "description": repo.description,
                "language": repo.language,
                "topics": repo.topics[:6],
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
            }
            for repo in repos[:10]
        ]
        prompt = {
            "profile": profile_blob,
            "top_languages": top_languages[:8],
            "top_topics": top_topics[:8],
            "repos": repos_blob,
            "response_schema": {
                "about_me": "single paragraph string",
                "professional_summary": "array of 3 short bullet strings",
                "skills": "array of up to 12 technical skills",
                "projects": [{"name": "repository name", "description": "enhanced 1-2 sentence description"}],
            },
        }

        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate concise, factual developer portfolio copy. "
                        "Return strict JSON only. Do not include markdown."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return None

        try:
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
            if not isinstance(parsed, dict):
                return None
            return parsed
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return None
