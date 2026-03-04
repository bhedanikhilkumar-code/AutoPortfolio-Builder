from __future__ import annotations

from collections import Counter
from html import escape
import hashlib
from io import BytesIO
import random
from zipfile import ZIP_DEFLATED, ZipFile

try:
    from fpdf import FPDF
except ModuleNotFoundError:  # pragma: no cover - exercised only when dependency is absent.
    FPDF = None

from app.schemas import (
    ExportRequest,
    GenerateRequest,
    PortfolioResponse,
    PortfolioSection,
    RepoSummary,
    ResumeTemplate,
)


TEMPLATE_IDS: tuple[str, ...] = ("classic", "modern", "minimal", "ats", "creative", "executive")
PDF_TEMPLATE_TRY_HISTORY: dict[str, list[str]] = {}


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
    top_languages = [name for name, _ in language_counts.most_common(8)]
    top_topics = [name for name, _ in topic_counts.most_common(8)]
    top_skills = top_languages or top_topics

    seed = _build_variant_seed(payload.profile.username, payload.variant_id, payload.try_index)
    rng = random.Random(seed)

    hero_templates = {
        1: [
            f"{display_name} builds software that ships.",
            f"{display_name} builds and ships high-impact software.",
            f"{display_name} turns ideas into production-ready products.",
            f"{display_name} delivers clean, fast, and reliable developer products.",
        ],
        2: [
            f"{display_name}'s journey is about building useful software with momentum.",
            f"From experiments to shipped tools, {display_name} keeps iterating with intent.",
            f"{display_name} builds products with story, purpose, and measurable impact.",
        ],
        3: [
            f"{display_name} | Software Engineer | Full-Stack Development | Automation.",
            f"{display_name} | Backend, APIs, UI Engineering, Delivery.",
            f"{display_name} | Engineer focused on scalable systems and execution.",
        ],
    }

    subheadline_templates = {
        1: [
            "Concise portfolio generated from real GitHub activity with impact-first positioning.",
            "Modern developer snapshot powered by repositories, commits, and practical outcomes.",
        ],
        2: [
            payload.profile.bio or "A detailed portfolio narrative derived from GitHub projects and engineering choices.",
            "A storytelling format that highlights journey, decisions, and project evolution.",
        ],
        3: [
            "ATS-ready profile with structured keywords, technical stack signals, and role relevance.",
            "Structured resume format optimized for recruiters and screening systems.",
        ],
    }

    about_variant = _build_about_summary(payload, display_name, top_languages, top_topics, payload.variant_id)

    project_items = [
        {
            "name": repo.name,
            "description": repo.description or "Repository with active development history.",
            "url": repo.html_url,
            "homepage": repo.homepage,
            "language": repo.language,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "topics": repo.topics,
        }
        for repo in featured_repos
    ]
    if payload.variant_id == 2:
        project_items = list(reversed(project_items))

    section_order = {
        1: ["hero", "projects", "skills", "about", "contact"],
        2: ["hero", "about", "projects", "skills", "contact"],
        3: ["hero", "skills", "projects", "about", "contact"],
    }[payload.variant_id]

    headline = (
        f"{display_name} builds software that ships."
        if payload.variant_id == 1 and payload.try_index == 1
        else rng.choice(hero_templates[payload.variant_id])
    )

    return PortfolioResponse(
        theme=payload.theme,
        hero=PortfolioSection(
            title="Hero",
            content={
                "headline": headline,
                "subheadline": rng.choice(subheadline_templates[payload.variant_id]),
                "stats": {
                    "public_repos": payload.profile.public_repos,
                    "followers": payload.profile.followers,
                    "following": payload.profile.following,
                },
                "cta": payload.profile.html_url,
                "variant_id": payload.variant_id,
                "try_index": payload.try_index,
                "section_order": section_order,
            },
        ),
        about=PortfolioSection(
            title="About",
            content={
                "name": display_name,
                "summary": about_variant,
                "github": payload.profile.html_url,
            },
        ),
        projects=PortfolioSection(
            title="Projects",
            content={"items": project_items},
        ),
        skills=PortfolioSection(
            title="Skills",
            content={
                "languages": top_languages,
                "topics": top_topics,
                "highlighted": _build_highlighted_skills(top_skills, payload.variant_id),
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


def _build_variant_seed(username: str, variant_id: int, try_index: int) -> int:
    token = f"{username.lower()}::{variant_id}::{try_index}".encode("utf-8")
    digest = hashlib.sha256(token).hexdigest()
    return int(digest[:16], 16)


def _build_about_summary(
    payload: GenerateRequest,
    display_name: str,
    top_languages: list[str],
    top_topics: list[str],
    variant_id: int,
) -> list[str]:
    base_location = f"Based in {payload.profile.location}" if payload.profile.location else None
    repo_line = (
        f"Maintains {len(payload.repos)} non-fork repositories on GitHub"
        if payload.repos
        else "Getting started with open source projects on GitHub"
    )

    if variant_id == 1:
        return [
            point
            for point in [
                payload.profile.bio,
                base_location,
                repo_line,
                f"Top stack: {', '.join(top_languages[:4])}" if top_languages else None,
            ]
            if point
        ]

    if variant_id == 2:
        return [
            point
            for point in [
                payload.profile.bio or f"{display_name} builds with a product mindset and iterative delivery style.",
                base_location,
                f"Portfolio story is inferred from {len(payload.repos)} repositories and contribution signals.",
                f"Frequently working across {', '.join(top_languages[:5])}." if top_languages else None,
                f"Domain interests include {', '.join(top_topics[:5])}." if top_topics else None,
            ]
            if point
        ]

    return [
        point
        for point in [
            payload.profile.bio or f"{display_name} focuses on software engineering execution.",
            base_location,
            repo_line,
            f"Core keywords: {', '.join((top_languages + top_topics)[:8])}" if (top_languages or top_topics) else None,
            "Strengths: API design, maintainable codebases, and delivery consistency.",
        ]
        if point
    ]


def _build_highlighted_skills(skills: list[str], variant_id: int) -> list[str]:
    if variant_id == 3:
        return [f"{skill} (Production)" for skill in skills[:8]]
    if variant_id == 2:
        return skills[:10]
    return skills[:8]


def build_export_filename(payload: ExportRequest) -> str:
    if payload.filename:
        return payload.filename

    name = payload.portfolio.about.content.get("name") or payload.portfolio.hero.content.get("headline") or "portfolio"
    slug = "".join(character.lower() if character.isalnum() else "-" for character in str(name))
    normalized = "-".join(part for part in slug.split("-") if part)
    return normalized[:64] or "portfolio"


def render_portfolio_html(portfolio: PortfolioResponse) -> str:
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    contact = portfolio.contact.content

    stats = hero.get("stats") or {}
    summary_items = _render_list_items(about.get("summary") or [])
    highlighted_skills = _render_tag_spans(skills.get("highlighted") or [])
    project_cards = "".join(_render_project_card(project) for project in projects.get("items") or [])
    contact_lines = _render_contact_lines(contact)
    display_name = _safe_text(about.get("name") or hero.get("headline") or "Portfolio")

    if not summary_items:
        summary_items = "<li>Details coming soon.</li>"
    if not highlighted_skills:
        highlighted_skills = "<span class=\"tag\">No skills listed</span>"
    if not project_cards:
        project_cards = "<p>No featured projects yet.</p>"
    if not contact_lines:
        contact_lines = "<p>No contact details listed.</p>"

    theme_class = "theme-minimal" if portfolio.theme == "minimal" else "theme-modern"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{display_name}</title>
  <style>
    :root {{
      --bg: linear-gradient(135deg, #f3efe6 0%, #d7e4f5 50%, #f7fafc 100%);
      --card: rgba(255, 255, 255, 0.9);
      --border: rgba(17, 24, 39, 0.12);
      --text: #10233f;
      --muted: #475569;
      --accent: #0f766e;
      --accent-2: #1d4ed8;
      --tag-bg: rgba(15, 118, 110, 0.08);
      --tag-text: #0f766e;
      --shadow: 0 20px 44px rgba(15, 23, 42, 0.14);
    }}

    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      min-height: 100vh;
      color: var(--text);
      background: var(--bg);
    }}

    * {{
      box-sizing: border-box;
    }}

    .theme-minimal {{
      --bg: #f5f5f4;
      --card: rgba(255, 255, 255, 0.98);
      --border: rgba(15, 23, 42, 0.08);
      --text: #111827;
      --muted: #44403c;
      --accent: #111827;
      --accent-2: #111827;
      --tag-bg: #f1f5f9;
      --tag-text: #1f2937;
      --shadow: none;
    }}

    main {{
      width: min(1080px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }}

    .grid {{
      display: grid;
      gap: 20px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}

    .panel {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 24px;
    }}

    .wide {{
      grid-column: 1 / -1;
    }}

    h1, h2, h3, p {{
      margin: 0;
    }}

    h1 {{
      font-size: clamp(2rem, 4vw, 4rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
      margin-bottom: 14px;
    }}

    h2 {{
      font-size: 1.2rem;
      margin-bottom: 16px;
    }}

    p, li {{
      color: var(--muted);
      line-height: 1.6;
    }}

    ul {{
      margin: 0;
      padding-left: 18px;
    }}

    .stats, .tags {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 16px;
    }}

    .stat {{
      min-width: 110px;
      padding: 14px;
      border-radius: 18px;
      background: rgba(16, 35, 63, 0.06);
    }}

    .theme-minimal .stat {{
      background: #f5f5f4;
    }}

    .stat strong {{
      display: block;
      font-size: 1.2rem;
      margin-bottom: 4px;
    }}

    .tag {{
      border-radius: 999px;
      padding: 8px 12px;
      background: var(--tag-bg);
      color: var(--tag-text);
      font-size: 0.9rem;
      font-weight: 600;
    }}

    .project-list {{
      display: grid;
      gap: 14px;
    }}

    .project {{
      padding: 18px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.76);
      border: 1px solid rgba(15, 23, 42, 0.08);
    }}

    .theme-minimal .project {{
      background: #fafaf9;
    }}

    .project-header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 8px;
    }}

    a {{
      color: var(--accent-2);
      text-decoration: none;
    }}

    @media (max-width: 640px) {{
      main {{
        width: calc(100% - 24px);
      }}

      .project-header {{
        flex-direction: column;
        align-items: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main class="{theme_class}">
    <section class="grid">
      <section class="panel wide">
        <p>{_safe_text(portfolio.hero.title)}</p>
        <h1>{_safe_text(hero.get("headline"))}</h1>
        <p>{_safe_text(hero.get("subheadline"))}</p>
        <div class="stats">
          {_render_stat("Repos", stats.get("public_repos", 0))}
          {_render_stat("Followers", stats.get("followers", 0))}
          {_render_stat("Following", stats.get("following", 0))}
        </div>
      </section>
      <section class="panel">
        <p>{_safe_text(portfolio.about.title)}</p>
        <h2>{display_name}</h2>
        <ul>{summary_items}</ul>
      </section>
      <section class="panel">
        <p>{_safe_text(portfolio.skills.title)}</p>
        <h2>Highlighted Skills</h2>
        <div class="tags">{highlighted_skills}</div>
      </section>
      <section class="panel wide">
        <p>{_safe_text(portfolio.projects.title)}</p>
        <h2>Featured Work</h2>
        <div class="project-list">{project_cards}</div>
      </section>
      <section class="panel wide">
        <p>{_safe_text(portfolio.contact.title)}</p>
        <h2>Contact</h2>
        {contact_lines}
      </section>
    </section>
  </main>
</body>
</html>
"""


def build_portfolio_zip(payload: ExportRequest) -> bytes:
    html_document = render_portfolio_html(payload.portfolio)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("index.html", html_document)
        archive.writestr("portfolio.json", payload.portfolio.model_dump_json(indent=2))
    return buffer.getvalue()


def render_portfolio_pdf(portfolio: PortfolioResponse, template_id: ResumeTemplate = "auto") -> bytes:
    resolved_template = _resolve_pdf_template(portfolio, template_id)

    if FPDF is None:
        return _render_portfolio_pdf_fallback(portfolio)

    if resolved_template == "ats":
        return _render_pdf_ats(portfolio)

    return _render_pdf_styled(portfolio, resolved_template)


def _resolve_pdf_template(portfolio: PortfolioResponse, template_id: ResumeTemplate) -> str:
    if template_id != "auto":
        return template_id

    profile_key = str(
        portfolio.about.content.get("name")
        or portfolio.contact.content.get("github")
        or portfolio.hero.content.get("headline")
        or "default"
    ).strip().lower()

    history = PDF_TEMPLATE_TRY_HISTORY.get(profile_key, [])
    available = [template for template in TEMPLATE_IDS if template not in history]
    if not available:
        history = []
        available = list(TEMPLATE_IDS)

    pick = random.choice(available)
    history = (history + [pick])[-3:]
    PDF_TEMPLATE_TRY_HISTORY[profile_key] = history
    return pick


def _render_pdf_styled(portfolio: PortfolioResponse, template_name: str) -> bytes:
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects_items = portfolio.projects.content.get("items") or []
    contact = portfolio.contact.content

    presets = {
        "classic": {"rail": (31, 41, 55), "bg": (248, 250, 252), "name": 23},
        "modern": {"rail": (17, 24, 39), "bg": (245, 247, 250), "name": 25},
        "minimal": {"rail": (60, 60, 60), "bg": (255, 255, 255), "name": 22},
        "creative": {"rail": (15, 23, 42), "bg": (239, 246, 255), "name": 26},
        "executive": {"rail": (20, 20, 20), "bg": (250, 250, 250), "name": 24},
    }
    style = presets.get(template_name, presets["modern"])

    display_name = _pdf_text(about.get("name") or hero.get("headline") or "Portfolio")
    headline = _pdf_text(hero.get("headline") or "")
    subheadline = _pdf_text(hero.get("subheadline") or "")

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    page_w, page_h = 210, 297
    margin = 10
    left_w = 60
    gutter = 8

    if template_name == "minimal":
        left_w = 0
        gutter = 0
    elif template_name == "modern":
        left_w = 48
    elif template_name == "creative":
        left_w = 42
    elif template_name == "executive":
        left_w = 52

    right_x = margin + left_w + gutter
    right_w = page_w - right_x - margin
    if template_name == "executive":
        right_x = margin
        right_w = page_w - margin - (left_w + margin + 6)

    pdf.set_fill_color(*style["bg"])
    pdf.rect(0, 0, page_w, page_h, style="F")

    if template_name == "minimal":
        pdf.set_draw_color(120, 120, 120)
        pdf.line(margin, 38, page_w - margin, 38)
    elif template_name == "executive":
        pdf.set_fill_color(*style["rail"])
        pdf.rect(page_w - (left_w + margin + 2), 0, left_w + margin + 2, page_h, style="F")
    else:
        pdf.set_fill_color(*style["rail"])
        pdf.rect(0, 0, left_w + margin + 2, page_h, style="F")

    if template_name == "creative":
        pdf.set_fill_color(30, 64, 175)
        pdf.rect(0, 0, page_w, 20, style="F")

    pdf.set_xy(right_x, 14)
    pdf.set_font("Helvetica", "B", style["name"])
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(right_w, 10, display_name)

    pdf.set_x(right_x)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(51, 65, 85)
    if headline:
        pdf.multi_cell(right_w, 6, headline)
    if subheadline:
        pdf.set_x(right_x)
        pdf.multi_cell(right_w, 6, subheadline)

    y = max(pdf.get_y() + 4, 56)

    def right_section(title: str, body_lines: list[str]) -> None:
        nonlocal y
        if y > 255:
            pdf.add_page()
            y = 20
        pdf.set_xy(right_x, y)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(17, 24, 39)
        pdf.multi_cell(right_w, 7, _pdf_text(title).upper())
        y = pdf.get_y() + 1
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 41, 59)
        for line in body_lines:
            if not line:
                continue
            pdf.set_xy(right_x, y)
            pdf.multi_cell(right_w, 5.4, f"- {_pdf_text(line)}")
            y = pdf.get_y()
        y += 3

    def left_section(title: str, body_lines: list[str], y_pos: float) -> float:
        pdf.set_xy(margin, y_pos)
        pdf.set_font("Helvetica", "B", 11.5)
        if template_name == "executive":
            pdf.set_text_color(30, 41, 59)
        else:
            pdf.set_text_color(226, 232, 240)
        pdf.multi_cell(left_w, 6.2, _pdf_text(title).upper())
        y_local = pdf.get_y() + 1
        pdf.set_font("Helvetica", "", 9.2)
        if template_name == "executive":
            pdf.set_text_color(51, 65, 85)
        else:
            pdf.set_text_color(203, 213, 225)
        for line in body_lines:
            if not line:
                continue
            pdf.set_xy(margin, y_local)
            pdf.multi_cell(left_w, 4.8, _pdf_text(line))
            y_local = pdf.get_y() + 0.6
        return y_local + 4

    contact_lines = [
        _pdf_text(contact.get("email")) if contact.get("email") else "",
        _pdf_text(contact.get("location")) if contact.get("location") else "",
        _pdf_text(contact.get("github")) if contact.get("github") else "",
        _pdf_text(contact.get("blog")) if contact.get("blog") else "",
    ]

    highlighted_skills = [str(item).strip() for item in skills.get("highlighted") or [] if str(item).strip()]
    about_points = [str(point).strip() for point in about.get("summary") or [] if str(point).strip()]

    if template_name != "minimal":
        left_y = 20
        left_y = left_section("Contact", [line for line in contact_lines if line], left_y)
        left_y = left_section("Technical Skills", highlighted_skills[:12], left_y)
        left_section("Summary", about_points[:6], left_y)
    else:
        pdf.set_xy(right_x, max(pdf.get_y() + 3, 44))
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(40, 40, 40)
        inline_contact = " | ".join([line for line in contact_lines if line])
        if inline_contact:
            pdf.multi_cell(right_w, 5.2, inline_contact)
        y = pdf.get_y() + 2

    order = {
        "classic": ["summary", "projects", "keywords"],
        "modern": ["summary", "projects", "keywords"],
        "minimal": ["projects", "summary", "keywords"],
        "creative": ["projects", "keywords", "summary"],
        "executive": ["summary", "keywords", "projects"],
    }.get(template_name, ["summary", "projects", "keywords"])

    project_lines: list[str] = []
    for project in projects_items[:5]:
        if not isinstance(project, dict):
            continue
        name = str(project.get("name") or "Untitled project")
        desc = str(project.get("description") or "Project details coming soon.")
        lang = str(project.get("language") or "")
        line = f"{name}: {desc}"
        if lang:
            line += f" | Tech: {lang}"
        project_lines.append(line)

    keywords = [str(x).strip() for x in (skills.get("languages") or []) + (skills.get("topics") or []) if str(x).strip()]

    for block in order:
        if block == "summary":
            right_section("Professional Summary", about_points or ["Details coming soon."])
        elif block == "projects":
            right_section("Project Experience", project_lines or ["No featured projects yet."])
        elif block == "keywords":
            right_section("Core Keywords", keywords[:14] or ["Software Engineering", "Web Development", "APIs", "Problem Solving"])

    output = pdf.output()
    return bytes(output) if not isinstance(output, bytes) else output


def _render_pdf_ats(portfolio: PortfolioResponse) -> bytes:
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects_items = portfolio.projects.content.get("items") or []
    contact = portfolio.contact.content

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(15, 12, 15)
    pdf.add_page()

    name = _pdf_text(about.get("name") or hero.get("headline") or "Portfolio")
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(180, 9, name)

    pdf.set_font("Helvetica", "", 10)
    github_value = str(contact.get("github") or "")
    github_short = github_value.rstrip("/").split("/")[-1] if github_value else ""
    contact_line = " | ".join(
        [
            _pdf_text(contact.get("email")) if contact.get("email") else "",
            _pdf_text(contact.get("location")) if contact.get("location") else "",
            _pdf_text(f"GitHub: {github_short}") if github_short else "",
        ]
    ).strip(" |")
    if contact_line:
        pdf.multi_cell(180, 6, contact_line)

    def sec(title: str) -> None:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(180, 7, _pdf_text(title).upper(), ln=True)
        pdf.set_font("Helvetica", "", 10)

    sec("Summary")
    for line in about.get("summary") or ["Details coming soon."]:
        pdf.multi_cell(180, 5.5, f"- {_pdf_text(line)}")

    sec("Skills")
    keywords = [str(x).strip() for x in (skills.get("languages") or []) + (skills.get("topics") or []) if str(x).strip()]
    pdf.multi_cell(180, 5.5, _pdf_text(", ".join(keywords[:24]) or "Software Engineering, APIs, Web Development"))

    sec("Projects")
    for project in projects_items[:6]:
        if not isinstance(project, dict):
            continue
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(180, 5.5, _pdf_text(project.get("name") or "Untitled project"))
        pdf.set_font("Helvetica", "", 10)
        desc = _pdf_text(project.get("description") or "Project details coming soon.")
        pdf.multi_cell(180, 5.2, desc)

    output = pdf.output()
    return bytes(output) if not isinstance(output, bytes) else output


def _render_stat(label: str, value: object) -> str:
    return (
        f"<div class=\"stat\"><strong>{_safe_text(value)}</strong>"
        f"<span>{_safe_text(label)}</span></div>"
    )


def _render_list_items(items: list[object]) -> str:
    return "".join(f"<li>{_safe_text(item)}</li>" for item in items if str(item).strip())


def _render_tag_spans(items: list[object]) -> str:
    return "".join(
        f"<span class=\"tag\">{_safe_text(item)}</span>"
        for item in items
        if str(item).strip()
    )


def _render_project_card(project: object) -> str:
    if not isinstance(project, dict):
        return ""

    tags = []
    language = project.get("language")
    if language:
        tags.append(language)
    tags.extend(project.get("topics") or [])
    tag_html = _render_tag_spans(tags)
    url = _safe_url(project.get("url"))
    description = _safe_text(project.get("description") or "Project details coming soon.")
    name = _safe_text(project.get("name") or "Untitled project")
    link_html = (
        f"<a href=\"{url}\" target=\"_blank\" rel=\"noreferrer\">Repository</a>"
        if url
        else ""
    )

    return f"""
<article class="project">
  <div class="project-header">
    <strong>{name}</strong>
    {link_html}
  </div>
  <p>{description}</p>
  <div class="tags">{tag_html}</div>
</article>
"""


def _render_contact_lines(contact: dict[str, object]) -> str:
    lines: list[str] = []

    github = _safe_url(contact.get("github"))
    if github:
        lines.append(
            f"<p><a href=\"{github}\" target=\"_blank\" rel=\"noreferrer\">{_safe_text(github)}</a></p>"
        )

    blog = _safe_url(contact.get("blog"))
    if blog:
        lines.append(
            f"<p><a href=\"{blog}\" target=\"_blank\" rel=\"noreferrer\">{_safe_text(blog)}</a></p>"
        )

    for field in ("email", "location"):
        value = contact.get(field)
        if value:
            lines.append(f"<p>{_safe_text(value)}</p>")

    return "".join(lines)


def _safe_text(value: object) -> str:
    return escape(str(value or ""))


def _safe_url(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith(("http://", "https://", "mailto:")):
        return escape(text, quote=True)
    return ""


def _pdf_text(value: object) -> str:
    return str(value or "").strip().encode("latin-1", "replace").decode("latin-1")


def _pdf_section_title(pdf: FPDF, text: object) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 22)
    pdf.multi_cell(0, 10, _pdf_text(text))


def _pdf_section_label(pdf: FPDF, text: object) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, _pdf_text(text))


def _pdf_paragraph(pdf: FPDF, text: object) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, _pdf_text(text))


def _pdf_bullet(pdf: FPDF, text: object) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, f"- {_pdf_text(text)}")


def _pdf_project(pdf: FPDF, name: object, details: object) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 7, _pdf_text(name))
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, _pdf_text(details))
    _pdf_spacer(pdf, 1)


def _pdf_spacer(pdf: FPDF, height: int) -> None:
    pdf.ln(height)


def _render_portfolio_pdf_fallback(portfolio: PortfolioResponse) -> bytes:
    lines = _collect_pdf_lines(portfolio)
    text_commands: list[str] = ["BT", "/F1 12 Tf", "14 TL", "50 792 Td"]

    for index, line in enumerate(lines):
        if index:
            text_commands.append("T*")
        text_commands.append(f"({_pdf_escape(line)}) Tj")

    text_commands.append("ET")
    stream = "\n".join(text_commands).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{index} 0 obj\n".encode("ascii"))
        buffer.write(obj)
        buffer.write(b"\nendobj\n")

    xref_position = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("ascii")
    )

    return buffer.getvalue()


def _collect_pdf_lines(portfolio: PortfolioResponse) -> list[str]:
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects_items = portfolio.projects.content.get("items") or []
    contact = portfolio.contact.content

    lines = [
        _pdf_text(about.get("name") or "Portfolio"),
        _pdf_text(hero.get("headline")),
        _pdf_text(hero.get("subheadline")),
        "",
        "About",
    ]

    about_points = about.get("summary") or ["Details coming soon."]
    lines.extend(f"- {_pdf_text(point)}" for point in about_points)
    lines.extend(["", "Skills"])

    highlighted_skills = [str(item).strip() for item in skills.get("highlighted") or [] if str(item).strip()]
    lines.append(_pdf_text(", ".join(highlighted_skills) if highlighted_skills else "No skills listed."))
    lines.extend(["", "Top Projects"])

    if projects_items:
        for project in projects_items[:4]:
            if not isinstance(project, dict):
                continue
            lines.append(_pdf_text(project.get("name") or "Untitled project"))
            lines.append(_pdf_text(project.get("description") or "Project details coming soon."))
            if project.get("language"):
                lines.append(_pdf_text(f"Language: {project['language']}"))
            if project.get("url"):
                lines.append(_pdf_text(f"Repository: {project['url']}"))
            lines.append("")
    else:
        lines.append("No featured projects yet.")
        lines.append("")

    lines.append("Contact")
    contact_lines = [
        f"GitHub: {contact.get('github')}" if contact.get("github") else "",
        f"Blog: {contact.get('blog')}" if contact.get("blog") else "",
        f"Email: {contact.get('email')}" if contact.get("email") else "",
        f"Location: {contact.get('location')}" if contact.get("location") else "",
    ]

    non_empty_contact_lines = [line for line in contact_lines if line]
    if non_empty_contact_lines:
        lines.extend(_pdf_text(f"- {line}") for line in non_empty_contact_lines)
    else:
        lines.append("No contact details listed.")

    return lines


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
