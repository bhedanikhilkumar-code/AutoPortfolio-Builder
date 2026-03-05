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

        providers = [
            self._provider_linkedin_public_page,
            self._provider_meta_only,
            self._provider_slug_inference,
        ]

        best: LinkedInProfile | None = None
        for provider in providers:
            try:
                candidate = await provider(slug, profile_url)
            except Exception:
                candidate = LinkedInProfile(
                    username=slug,
                    url=profile_url,
                    summary=["LinkedIn provider failed; fallback applied."],
                    provider_used="provider_exception_fallback",
                    confidence_score=0.08,
                    signals=["provider_exception"],
                )
            if best is None or candidate.confidence_score > best.confidence_score:
                best = candidate
            if candidate.confidence_score >= 0.8:
                break

        if best is None:
            best = LinkedInProfile(
                username=slug,
                url=profile_url,
                summary=["LinkedIn profile connected."],
                provider_used="global_fallback",
                confidence_score=0.05,
                signals=["empty_chain_fallback"],
            )

        self._cache[slug] = (now, best)
        return best

    async def _provider_linkedin_public_page(self, slug: str, profile_url: str) -> LinkedInProfile:
        title = ""
        headline = ""
        summary: list[str] = []
        signals: list[str] = []

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
            if title:
                signals.append("title")

            headline = _extract_headline(html)
            if headline:
                signals.append("headline")

            summary = _extract_summary(html)
            if summary:
                signals.append("summary")

            if headline and headline not in summary:
                summary.insert(0, headline)
            if not summary and title:
                summary = [f"LinkedIn profile: {title}"]
            if not summary:
                summary = ["LinkedIn profile connected."]

            confidence = _score_confidence(signals, response.status_code)
            return LinkedInProfile(
                username=slug,
                url=profile_url,
                title=title or None,
                headline=headline or None,
                summary=summary[:4],
                provider_used="linkedin_public_page",
                confidence_score=confidence,
                signals=signals,
            )
        except httpx.HTTPError:
            return LinkedInProfile(
                username=slug,
                url=profile_url,
                summary=["LinkedIn profile connected (public preview unavailable right now)."],
                provider_used="linkedin_public_page",
                confidence_score=0.15,
                signals=["network_fallback"],
            )

    async def _provider_meta_only(self, slug: str, profile_url: str) -> LinkedInProfile:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                response = await client.get(profile_url)
                html = response.text
            headline = _extract_headline(html)
            title = _extract_title(html)
            summary = [x for x in [headline, title and f"LinkedIn profile: {title}"] if x]
            if not summary:
                summary = ["LinkedIn profile connected."]
            signals = ["meta_only"] if headline or title else ["meta_fallback"]
            return LinkedInProfile(
                username=slug,
                url=profile_url,
                title=title or None,
                headline=headline or None,
                summary=summary[:3],
                provider_used="linkedin_meta_only",
                confidence_score=0.45 if (headline or title) else 0.2,
                signals=signals,
            )
        except httpx.HTTPError:
            return LinkedInProfile(
                username=slug,
                url=profile_url,
                summary=["LinkedIn profile connected."],
                provider_used="linkedin_meta_only",
                confidence_score=0.1,
                signals=["meta_network_fallback"],
            )

    async def _provider_slug_inference(self, slug: str, profile_url: str) -> LinkedInProfile:
        inferred_name = slug.replace("-", " ").title()
        return LinkedInProfile(
            username=slug,
            url=profile_url,
            title=inferred_name,
            headline="LinkedIn username inferred profile",
            summary=[f"LinkedIn profile inferred from username: {slug}"],
            provider_used="slug_inference",
            confidence_score=0.25,
            signals=["slug_inference"],
        )


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


def _score_confidence(signals: list[str], status_code: int) -> float:
    score = 0.15
    if status_code == 200:
        score += 0.2
    if "title" in signals:
        score += 0.2
    if "headline" in signals:
        score += 0.25
    if "summary" in signals:
        score += 0.2
    return min(1.0, score)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
