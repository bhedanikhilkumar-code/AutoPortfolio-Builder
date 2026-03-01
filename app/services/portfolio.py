from __future__ import annotations

from collections import Counter

from app.schemas import GenerateRequest, PortfolioResponse, PortfolioSection, RepoSummary


def generate_portfolio(payload: GenerateRequest) -> PortfolioResponse:
    featured_repos = _select_featured_repos(payload.repos)
    language_counts = Counter(
        repo.language.strip()
        for repo in payload.repos
        if repo.language and repo.language.strip()
    )
    topic_counts = Counter(
        topic.strip()
        for repo in payload.repos
        for topic in repo.topics
        if topic.strip()
    )

    display_name = payload.profile.name or payload.profile.username
    about_points = [
        point
        for point in [
            payload.profile.bio,
            f"Based in {payload.profile.location}" if payload.profile.location else None,
            (
                f"Maintains {len(payload.repos)} non-fork repositories on GitHub"
                if payload.repos
                else "Getting started with open source projects on GitHub"
            ),
        ]
        if point
    ]
    top_skills = [name for name, _ in language_counts.most_common(8)] or [
        topic for topic, _ in topic_counts.most_common(8)
    ]

    return PortfolioResponse(
        hero=PortfolioSection(
            title="Hero",
            content={
                "headline": f"{display_name} builds software that ships.",
                "subheadline": payload.profile.bio
                or "GitHub-powered portfolio generated automatically from live repository data.",
                "stats": {
                    "public_repos": payload.profile.public_repos,
                    "followers": payload.profile.followers,
                    "following": payload.profile.following,
                },
                "cta": payload.profile.html_url,
            },
        ),
        about=PortfolioSection(
            title="About",
            content={
                "name": display_name,
                "summary": about_points,
                "github": payload.profile.html_url,
            },
        ),
        projects=PortfolioSection(
            title="Projects",
            content={
                "items": [
                    {
                        "name": repo.name,
                        "description": repo.description
                        or "Repository with active development history.",
                        "url": repo.html_url,
                        "homepage": repo.homepage,
                        "language": repo.language,
                        "stars": repo.stargazers_count,
                        "forks": repo.forks_count,
                        "topics": repo.topics,
                    }
                    for repo in featured_repos
                ]
            },
        ),
        skills=PortfolioSection(
            title="Skills",
            content={
                "languages": [name for name, _ in language_counts.most_common(8)],
                "topics": [name for name, _ in topic_counts.most_common(8)],
                "highlighted": top_skills,
            },
        ),
        contact=PortfolioSection(
            title="Contact",
            content={
                "github": payload.profile.html_url,
                "email": payload.profile.email,
                "blog": payload.profile.blog,
                "location": payload.profile.location,
            },
        ),
    )


def _select_featured_repos(repos: list[RepoSummary]) -> list[RepoSummary]:
    ranked = sorted(
        repos,
        key=lambda repo: (
            repo.stargazers_count,
            repo.forks_count,
            int(bool(repo.description)),
            repo.updated_at or "",
        ),
        reverse=True,
    )
    return ranked[:6]
