from __future__ import annotations

from typing import Annotated, Any, Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


ThemeMode = Literal["modern", "minimal"]
ResumeTemplate = Literal["auto", "classic", "modern", "minimal", "ats", "creative", "executive"]
GitHubInput = Annotated[str, Field(min_length=1, max_length=512)]


LinkedInUsername = Annotated[str, Field(min_length=3, max_length=256)]


class ProfileRequest(BaseModel):
    username: GitHubInput
    linkedin_username: LinkedInUsername | None = None


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


class ManualInput(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=80)]
    email: Annotated[str, Field(min_length=5, max_length=200)]
    github: Annotated[str, Field(min_length=1, max_length=512)]
    linkedin: Annotated[str, Field(max_length=256)] = ""
    skills: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(default_factory=list)
    projects: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    profile: GitHubProfile
    repos: list[RepoSummary]
    linkedin: LinkedInProfile
    theme: ThemeMode = "modern"
    variant_id: Literal[1, 2, 3] = 1
    try_index: Annotated[int, Field(ge=1)] = 1
    target_role: Literal["frontend", "backend", "fullstack", "data", "ai"] | None = None
    deep_mode: bool = True
    manual_input: ManualInput | None = None


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
    name: Annotated[str, Field(min_length=2, max_length=80)]
    email: str
    password: Annotated[str, Field(min_length=8, max_length=128)]


class LoginRequest(BaseModel):
    email: str
    password: Annotated[str, Field(min_length=8, max_length=128)]


class GoogleAuthRequest(BaseModel):
    id_token: Annotated[str, Field(min_length=16)]


class GoogleAccessTokenRequest(BaseModel):
    access_token: Annotated[str, Field(min_length=16)]


class GoogleAuthConfigResponse(BaseModel):
    enabled: bool
    client_id: str | None = None


class GoogleAuthStartResponse(BaseModel):
    enabled: bool
    auth_url: str | None = None


class GitHubAuthStartResponse(BaseModel):
    enabled: bool
    auth_url: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    email_verified: bool = True
    message: str | None = None


class VerificationRequest(BaseModel):
    email: str


class VerificationResponse(BaseModel):
    ok: bool = True
    message: str


class VerificationStatusResponse(BaseModel):
    email: str
    email_verified: bool


class AvatarResponse(BaseModel):
    avatar_url: str | None = None
    social_avatar_url: str | None = None
    custom_avatar_url: str | None = None


class UserSummary(BaseModel):
    id: int
    name: str | None = None
    email: str
    avatar_url: str | None = None
    social_avatar_url: str | None = None
    custom_avatar_url: str | None = None
    email_verified: bool = False
    is_admin: bool = False
    is_active: bool = True
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


class AdminStatsResponse(BaseModel):
    total_users: int
    total_admins: int
    total_resumes: int
    total_drafts: int
    total_published: int
    total_generations: int


class AdminUserItem(BaseModel):
    id: int
    email: str
    is_admin: bool
    is_active: bool
    resume_count: int
    generation_count: int
    created_at: datetime


class AdminUsersResponse(BaseModel):
    users: list[AdminUserItem]
    total: int
    page: int
    page_size: int


class AdminResumeItem(BaseModel):
    id: int
    user_id: int
    owner_email: str
    title: str
    status: str
    updated_at: datetime


class AdminResumesResponse(BaseModel):
    resumes: list[AdminResumeItem]
    total: int
    page: int
    page_size: int


class AdminActivityItem(BaseModel):
    id: int
    admin_user_id: int
    action: str
    target_type: str
    target_id: int
    details: str | None = None
    created_at: datetime


class AdminActivityResponse(BaseModel):
    logs: list[AdminActivityItem]
    total: int
    page: int
    page_size: int


class AdminActionResponse(BaseModel):
    ok: bool = True
    message: str


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


# New schemas - ATS Analysis & Exports
class ATSAnalysisRequest(BaseModel):
    portfolio: PortfolioResponse
    target_role: Literal["frontend", "backend", "fullstack", "data", "ai"] | None = None


class ATSAnalysisResponse(BaseModel):
    overall_score: int
    keyword_score: int
    format_score: int
    readability_score: int
    completeness_score: int
    improvements: list[str]
    missing_keywords: list[str]
    role_scores: dict[str, int]


class RoleRecommendationResponse(BaseModel):
    recommended_role: str
    role_scores: dict[str, dict[str, int]]


class ExportFormatRequest(BaseModel):
    portfolio: PortfolioResponse
    format: Literal["markdown", "json", "latex", "html"]


class ExportFormatResponse(BaseModel):
    format: str
    content: str
    content_type: str


class APIKeyCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=64)]
    rate_limit: int = Field(default=100, ge=10, le=1000)



class APIKeyResponse(BaseModel):
    key_id: str
    key: str
    name: str
    rate_limit: int
    created_at: datetime


# Webhook schemas
class WebhookRequest(BaseModel):
    url: Annotated[str, Field(min_length=10, max_length=512)]
    events: Annotated[list[str], Field(min_length=1)]
    name: Annotated[str, Field(max_length=64)] = "default"


class WebhookResponse(BaseModel):
    webhook_id: str
    secret: str
    name: str
    url: str
    events: list[str]
    created_at: datetime


class WebhookListResponse(BaseModel):
    webhooks: list[dict[str, Any]]


# Theme schemas
class ThemeInfo(BaseModel):
    id: str
    name: str
    primary: str
    secondary: str
    background: str
    text: str
    accent: str


class ThemeListResponse(BaseModel):
    themes: list[ThemeInfo]


class ThemeCSSRequest(BaseModel):
    theme_id: str
    custom_css: str | None = None
    font_family: str = "Inter"


class ThemeCSSResponse(BaseModel):
    theme_id: str
    css: str


# SEO schemas
class SEOAnalysisRequest(BaseModel):
    portfolio: PortfolioResponse


class SEOAnalysisResponse(BaseModel):
    score: int
    grade: str
    improvements: list[str]


class SEOMetaResponse(BaseModel):
    title: str
    description: str
    keywords: str
    og_tags: str
    twitter_tags: str
    jsonld: str


# Preview schemas
class PreviewRequest(BaseModel):
    portfolio: PortfolioResponse
    theme_id: str = "modern"
    inject_seo: bool = False


class PreviewResponse(BaseModel):
    html: str


class MultiThemePreviewRequest(BaseModel):
    portfolio: PortfolioResponse
    theme_ids: list[str]


class MultiThemePreviewResponse(BaseModel):
    previews: dict[str, str]


# PDF Template schemas
class PDFTemplateListResponse(BaseModel):
    templates: list[dict[str, str]]


class PDFExportRequest(BaseModel):
    portfolio: PortfolioResponse
    template: Literal["modern", "classic", "minimal", "creative", "executive", "gradient"] = "modern"
    include_seo: bool = True


class PDFExportResponse(BaseModel):
    success: bool
    message: str


# Project Manager schemas
class ReorderProjectsRequest(BaseModel):
    portfolio: PortfolioResponse
    new_order: list[str]


class FilterProjectsRequest(BaseModel):
    portfolio: PortfolioResponse
    language: str


class AddProjectRequest(BaseModel):
    portfolio: PortfolioResponse
    project: dict[str, Any]


class UpdateProjectRequest(BaseModel):
    portfolio: PortfolioResponse
    project_name: str
    updates: dict[str, Any]


class ProjectsSummaryResponse(BaseModel):
    total_projects: int
    total_stars: int
    total_forks: int
    languages: dict[str, int]
    most_starred: str


# Notifications schemas
class NotificationListResponse(BaseModel):
    notifications: list[dict[str, Any]]
    unread_count: int


# Interview Prep schemas
class InterviewQuestionsRequest(BaseModel):
    portfolio: PortfolioResponse
    role: Literal["general", "frontend", "backend", "fullstack", "data", "ai"] = "general"


class InterviewQuestionsResponse(BaseModel):
    questions: list[str]
    count: int
    estimated_duration_minutes: int


class MockInterviewResponse(BaseModel):
    questions: list[dict[str, str]]


class AnswerSuggestionsRequest(BaseModel):
    portfolio: PortfolioResponse
    question: str


class AnswerSuggestionsResponse(BaseModel):
    suggestions: list[str]


# Portfolio Analytics schemas
class TrackViewRequest(BaseModel):
    portfolio_id: int
    viewer_ip: str | None = None
    referrer: str | None = None


class PortfolioStatsResponse(BaseModel):
    total_views: int
    views_over_time: list[dict[str, Any]]
    top_referrers: list[dict[str, Any]]
    avg_daily_views: float


# Auto Deploy schemas
class DeployConfigRequest(BaseModel):
    provider: Literal["github", "vercel", "netlify"]
    username: str | None = None
    custom_domain: str | None = None


class DeployConfigResponse(BaseModel):
    yaml: str | None = None
    toml: str | None = None
    config_json: dict | None = None
    script: str | None = None
    provider: str


# i18n schemas
class LanguageListResponse(BaseModel):
    languages: list[dict[str, str]]


class TranslateRequest(BaseModel):
    portfolio: PortfolioResponse
    target_lang: str


class TranslateResponse(BaseModel):
    original_language: str
    translated_language: str
    translated_content: dict
    note: str


# Cover Letter schemas
class CoverLetterRequest(BaseModel):
    portfolio: PortfolioResponse
    company_name: str = "the hiring team"
    position: str = "the position"
    job_description: str | None = None


class CoverLetterResponse(BaseModel):
    subject: str
    body: str
    name: str
    email: str


# Job Tracker schemas
class JobApplicationRequest(BaseModel):
    company: str
    position: str
    portfolio_url: str | None = None


class JobApplicationResponse(BaseModel):
    id: str
    company: str
    position: str
    status: str
    portfolio_url: str | None = None


class JobStatsResponse(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    response_rate: float


# GitHub README schemas
class GitHubReadmeRequest(BaseModel):
    portfolio: PortfolioResponse


class GitHubReadmeResponse(BaseModel):
    readme: str


# QR Code & vCard schemas
class QRCodeRequest(BaseModel):
    portfolio_url: str
    size: int = 300


class QRCodeResponse(BaseModel):
    qr_url: str
    data: str


class VCardRequest(BaseModel):
    portfolio: PortfolioResponse


class VCardResponse(BaseModel):
    vcard: str
