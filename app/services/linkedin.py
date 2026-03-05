from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

import httpx

from app.schemas import LinkedInProfile


@dataclass(slots=True)
class LinkedInService:
    timeout_seconds: float = 8.0
    cache_ttl_seconds: int = 900
    _cache: dict[str, tuple[float, LinkedInProfile]] = field(default_factory=dict)

    async def fetch_public_profile(self, username: str) -> LinkedInProfile:
        slug = _normalize_slug(username)
        now = time.time()
        cached = self._cache.get(slug)
        if cached and now - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        profile_url = f"https://www.linkedin.com/in/{slug}/"
        title = ""
        headline = ""
        summary: list[str] = []

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

            title = _extract_title(html)
            headline = _extract_headline(html)
            summary = _extract_summary(html)

            if headline and headline not in summary:
                summary.insert(0, headline)
            if not summary and title:
                summary = [f"LinkedIn profile: {title}"]
            if not summary:
                summary = ["LinkedIn profile connected."]

        except httpx.HTTPError:
            summary = ["LinkedIn profile connected (public preview unavailable right now)."]

        profile = LinkedInProfile(
            username=slug,
            url=profile_url,
            title=title or None,
            headline=headline or None,
            summary=summary[:4],
        )
        self._cache[slug] = (now, profile)
        return profile


def _normalize_slug(value: str) -> str:
    raw = value.strip().strip("/")
    if raw.startswith("http://") or raw.startswith("https://"):
        raw = raw.rstrip("/").split("/")[-1]
    raw = raw.replace("in/", "").strip()
    return re.sub(r"[^a-zA-Z0-9-]", "", raw) or "unknown"


def _extract_title(html: str) -> str:
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not title_match:
        return ""
    return _clean(title_match.group(1)).replace("| LinkedIn", "").strip(" -")


def _extract_headline(html: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            text = _clean(match.group(1))
            if text:
                return text
    return ""


def _extract_summary(html: str) -> list[str]:
    points: list[str] = []

    for script_match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        raw = script_match.group(1).strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates = payload if isinstance(payload, list) else [payload]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            for key in ("description", "headline", "jobTitle"):
                val = item.get(key)
                if isinstance(val, str) and _clean(val):
                    points.append(_clean(val))

    deduped: list[str] = []
    seen: set[str] = set()
    for point in points:
        key = point.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(point)
    return deduped[:3]


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
