from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from app.schemas import LinkedInProfile


@dataclass(slots=True)
class LinkedInService:
    timeout_seconds: float = 8.0

    async def fetch_public_profile(self, username: str) -> LinkedInProfile:
        normalized = username.strip().strip("/")
        if normalized.startswith("http://") or normalized.startswith("https://"):
            slug = normalized.rstrip("/").split("/")[-1]
        else:
            slug = normalized

        slug = slug.replace("in/", "").strip()
        profile_url = f"https://www.linkedin.com/in/{slug}/"

        title = ""
        headline = ""
        summary = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    profile_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
                html = response.text

            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = _clean(title_match.group(1)).replace("| LinkedIn", "").strip(" -")

            desc_match = re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
                html,
                re.IGNORECASE | re.DOTALL,
            )
            if desc_match:
                headline = _clean(desc_match.group(1))

            if headline:
                summary = [headline]
            elif title:
                summary = [f"LinkedIn profile: {title}"]
            else:
                summary = ["LinkedIn profile connected."]
        except httpx.HTTPError:
            summary = ["LinkedIn profile connected (public preview unavailable right now)."]

        return LinkedInProfile(username=slug, url=profile_url, title=title or None, headline=headline or None, summary=summary)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
