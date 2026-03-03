from __future__ import annotations

from collections import Counter
from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

try:
    from fpdf import FPDF
except ModuleNotFoundError:  # pragma: no cover - exercised only when dependency is absent.
    FPDF = None

from app.schemas import ExportRequest, GenerateRequest, PortfolioResponse, PortfolioSection, RepoSummary


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
        theme=payload.theme,
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


def render_portfolio_pdf(portfolio: PortfolioResponse) -> bytes:
    if FPDF is None:
        return _render_portfolio_pdf_fallback(portfolio)

    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects_items = portfolio.projects.content.get("items") or []
    contact = portfolio.contact.content

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_title(_pdf_text(about.get("name") or hero.get("headline") or "Portfolio"))
    pdf.set_author(_pdf_text(contact.get("github") or "AutoPortfolio Builder"))
    pdf.set_margins(15, 15, 15)

    _pdf_section_title(pdf, about.get("name") or "Portfolio")
    _pdf_paragraph(pdf, hero.get("headline"))
    _pdf_paragraph(pdf, hero.get("subheadline"))

    _pdf_spacer(pdf, 2)
    _pdf_section_label(pdf, "About")
    about_points = about.get("summary") or []
    if about_points:
        for point in about_points:
            _pdf_bullet(pdf, point)
    else:
        _pdf_bullet(pdf, "Details coming soon.")

    _pdf_spacer(pdf, 2)
    _pdf_section_label(pdf, "Skills")
    highlighted_skills = [str(item).strip() for item in skills.get("highlighted") or [] if str(item).strip()]
    _pdf_paragraph(pdf, ", ".join(highlighted_skills) if highlighted_skills else "No skills listed.")

    _pdf_spacer(pdf, 2)
    _pdf_section_label(pdf, "Top Projects")
    if projects_items:
        for project in projects_items[:4]:
            if not isinstance(project, dict):
                continue
            project_name = project.get("name") or "Untitled project"
            description = project.get("description") or "Project details coming soon."
            details = [description]
            if project.get("language"):
                details.append(f"Language: {project['language']}")
            if project.get("url"):
                details.append(f"Repository: {project['url']}")
            _pdf_project(pdf, project_name, " | ".join(details))
    else:
        _pdf_paragraph(pdf, "No featured projects yet.")

    _pdf_spacer(pdf, 2)
    _pdf_section_label(pdf, "Contact")
    contact_lines = [
        f"GitHub: {contact.get('github')}" if contact.get("github") else "",
        f"Blog: {contact.get('blog')}" if contact.get("blog") else "",
        f"Email: {contact.get('email')}" if contact.get("email") else "",
        f"Location: {contact.get('location')}" if contact.get("location") else "",
    ]
    for line in contact_lines:
        if line:
            _pdf_bullet(pdf, line)
    if not any(contact_lines):
        _pdf_paragraph(pdf, "No contact details listed.")

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
    pdf.set_font("Helvetica", "B", 22)
    pdf.multi_cell(0, 10, _pdf_text(text))


def _pdf_section_label(pdf: FPDF, text: object) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, _pdf_text(text))


def _pdf_paragraph(pdf: FPDF, text: object) -> None:
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, _pdf_text(text))


def _pdf_bullet(pdf: FPDF, text: object) -> None:
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 6, f"- {_pdf_text(text)}")


def _pdf_project(pdf: FPDF, name: object, details: object) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 7, _pdf_text(name))
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
