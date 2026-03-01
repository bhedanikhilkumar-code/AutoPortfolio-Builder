from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


class ProfileRequest(BaseModel):
    username: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9-]+$")


class RepoSummary(BaseModel):
    name: str
    description: str | None = None
    html_url: str
    homepage: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class GitHubProfile(BaseModel):
    username: str
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    html_url: str
    blog: str | None = None
    location: str | None = None
    email: str | None = None
    public_repos: int = 0
    followers: int = 0
    following: int = 0


class ProfileResponse(BaseModel):
    profile: GitHubProfile
    repos: list[RepoSummary]


class GenerateRequest(BaseModel):
    profile: GitHubProfile
    repos: list[RepoSummary]


class PortfolioSection(BaseModel):
    title: str
    content: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class PortfolioResponse(BaseModel):
    hero: PortfolioSection
    about: PortfolioSection
    projects: PortfolioSection
    skills: PortfolioSection
    contact: PortfolioSection
