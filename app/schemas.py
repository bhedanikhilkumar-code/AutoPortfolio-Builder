from __future__ import annotations

from typing import Annotated, Any, Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


ThemeMode = Literal["modern", "minimal"]
ResumeTemplate = Literal["auto", "classic", "modern", "minimal", "ats", "creative", "executive"]
GitHubUsername = Annotated[str, Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9-]+$")]


LinkedInUsername = Annotated[str, Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9-]+$")]


class ProfileRequest(BaseModel):
    username: GitHubUsername
    linkedin_username: LinkedInUsername


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


class LinkedInProfile(BaseModel):
    username: str
    url: str
    title: str | None = None
    headline: str | None = None
    summary: list[str] = Field(default_factory=list)
    provider_used: str = "linkedin_public_page"
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    profile: GitHubProfile
    repos: list[RepoSummary]
    linkedin: LinkedInProfile | None = None


class GenerateRequest(BaseModel):
    profile: GitHubProfile
    repos: list[RepoSummary]
    linkedin: LinkedInProfile
    theme: ThemeMode = "modern"
    variant_id: Literal[1, 2, 3] = 1
    try_index: Annotated[int, Field(ge=1)] = 1
    target_role: Literal["frontend", "backend", "fullstack", "data", "ai"] | None = None
    deep_mode: bool = True


class PortfolioSection(BaseModel):
    title: str
    content: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class PortfolioResponse(BaseModel):
    theme: ThemeMode
    hero: PortfolioSection
    about: PortfolioSection
    projects: PortfolioSection
    skills: PortfolioSection
    contact: PortfolioSection


ExportFilename = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"),
]


class ExportRequest(BaseModel):
    portfolio: PortfolioResponse
    filename: ExportFilename | None = None
    template_id: ResumeTemplate = "auto"


class ShareRequest(BaseModel):
    portfolio: PortfolioResponse
    filename: ExportFilename | None = None
    use_short_link: bool = True


class ShareResponse(BaseModel):
    share_id: str
    resume_url: str
    share_url: str


class RegisterRequest(BaseModel):
    email: str
    password: Annotated[str, Field(min_length=8, max_length=128)]


class LoginRequest(BaseModel):
    email: str
    password: Annotated[str, Field(min_length=8, max_length=128)]


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserSummary(BaseModel):
    id: int
    email: str
    created_at: datetime


class ResumeCard(BaseModel):
    id: int
    title: str
    status: str
    updated_at: datetime


class GenerationHistoryItem(BaseModel):
    id: int
    username: str
    variant_id: int
    template_id: str
    created_at: datetime


class DashboardResponse(BaseModel):
    user: UserSummary
    my_resumes: list[ResumeCard]
    saved_drafts: list[ResumeCard]
    generation_history: list[GenerationHistoryItem]
    analytics: AnalyticsSummary | None = None


class SaveResumeRequest(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    portfolio: PortfolioResponse
    status: Literal["draft", "published"] = "draft"


class SaveResumeResponse(BaseModel):
    resume_id: int
    message: str


class ResumeVersionItem(BaseModel):
    id: int
    resume_id: int
    version_number: int
    created_at: datetime


class ResumeVersionsResponse(BaseModel):
    versions: list[ResumeVersionItem]


class RestoreVersionResponse(BaseModel):
    resume_id: int
    restored_version: int
    message: str


class RewriteRequest(BaseModel):
    section: Literal["summary", "projects", "skills"]
    mode: Literal["concise", "ats", "storytelling"]
    text: str
    target_role: Literal["frontend", "backend", "fullstack", "data", "ai"] | None = None


class RewriteResponse(BaseModel):
    rewritten_text: str


class BrandingSettingsRequest(BaseModel):
    palette: str = "default"
    font_family: str = "Inter"
    logo_url: str | None = None


class BrandingSettingsResponse(BaseModel):
    palette: str
    font_family: str
    logo_url: str | None = None


class DeployExportRequest(BaseModel):
    portfolio: PortfolioResponse
    provider: Literal["netlify", "vercel"]
    filename: ExportFilename | None = None


class DeployExportResponse(BaseModel):
    provider: Literal["netlify", "vercel"]
    preview_url: str


class AnalyticsSummary(BaseModel):
    total_views: int
    total_project_clicks: int
    top_projects: list[dict[str, int]]


class APIError(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: APIError
