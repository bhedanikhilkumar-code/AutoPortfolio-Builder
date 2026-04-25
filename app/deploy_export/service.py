from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

from app.schemas import DeployExportRequest, PortfolioResponse
from app.services.portfolio import render_portfolio_html


def build_deploy_package(payload: DeployExportRequest) -> bytes:
    html = render_portfolio_html(payload.portfolio)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("index.html", html)
        if payload.provider == "netlify":
            archive.writestr("netlify.toml", "[build]\npublish = '.'\n")
        else:
            archive.writestr("vercel.json", '{"cleanUrls": true}')
    return buffer.getvalue()


def export_portfolio_markdown(portfolio: PortfolioResponse) -> str:
    """Export portfolio as Markdown for GitHub README."""
    lines = []
    
    # Hero section
    hero = portfolio.hero.content
    lines.append(f"# {hero.get('headline', 'Portfolio')}\n")
    lines.append(f"*{hero.get('subheadline', '')}*\n")
    
    # Stats
    stats = hero.get('stats', {})
    if stats:
        lines.append("### 📊 Stats")
        lines.append(f"- Public Repos: {stats.get('public_repos', 0)}")
        lines.append(f"- Followers: {stats.get('followers', 0)}")
        lines.append(f"- Following: {stats.get('following', 0)}\n")
    
    # About
    about = portfolio.about.content
    lines.append("## 👤 About")
    lines.append(f"**{about.get('name', '')}**\n")
    for point in about.get('summary', []):
        lines.append(f"- {point}")
    lines.append("")
    
    # Skills
    skills = portfolio.skills.content
    lines.append("## 🛠️ Skills")
    for skill in skills.get('highlighted', []):
        lines.append(f"- {skill}")
    lines.append("")
    
    # Projects
    projects = portfolio.projects.content
    lines.append("## 📁 Projects")
    for item in projects.get('items', []):
        if isinstance(item, dict):
            lines.append(f"### {item.get('name', 'Untitled')}")
            if item.get('description'):
                lines.append(f"{item.get('description')}")
            if item.get('language'):
                lines.append(f"- **Language**: {item.get('language')}")
            if item.get('stars'):
                lines.append(f"- ⭐ {item.get('stars')} stars")
            if item.get('url'):
                lines.append(f"- [View Repo]({item.get('url')})")
            lines.append("")
    
    # Contact
    contact = portfolio.contact.content
    lines.append("## 📧 Contact")
    if contact.get('github'):
        lines.append(f"- [GitHub]({contact.get('github')})")
    if contact.get('linkedin'):
        lines.append(f"- [LinkedIn]({contact.get('linkedin')})")
    if contact.get('email'):
        lines.append(f"- Email: {contact.get('email')}")
    if contact.get('location'):
        lines.append(f"- Location: {contact.get('location')}")
    
    return "\n".join(lines)


def export_portfolio_json(portfolio: PortfolioResponse) -> str:
    """Export portfolio as structured JSON."""
    return json.dumps(portfolio.model_dump(mode='json'), indent=2)


def export_portfolio_latex(portfolio: PortfolioResponse) -> str:
    """Export portfolio as LaTeX for Overleaf."""
    lines = [
        r"\documentclass{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{enumitem}",
        r"\usepackage{hyperref}",
        r"\hypersetup{colorlinks=true,urlcolor=blue}",
        r"\begin{document}",
        "",
    ]
    
    # Name & Headline
    hero = portfolio.hero.content
    about = portfolio.about.content
    lines.append(r"\textbf{" + (about.get('name', 'Portfolio') or 'Portfolio') + r"}\par")
    lines.append(hero.get('headline', '') + r"\par")
    lines.append(hero.get('subheadline', '') + r"\par")
    lines.append(r"\vspace{0.5em}")
    
    # About
    lines.append(r"\section*{About}")
    for point in about.get('summary', []):
        lines.append(point + r"\\")
    lines.append("")
    
    # Skills
    skills = portfolio.skills.content
    lines.append(r"\section*{Skills}")
    skills_list = skills.get('highlighted', [])
    lines.append(r"\begin{itemize}")
    for skill in skills_list:
        lines.append(r"\item " + skill)
    lines.append(r"\end{itemize}")
    lines.append("")
    
    # Projects
    projects = portfolio.projects.content
    lines.append(r"\section*{Projects}")
    lines.append(r"\begin{itemize}")
    for item in projects.get('items', []):
        if isinstance(item, dict):
            lines.append(r"\item \textbf{" + (item.get('name', 'Untitled') or 'Untitled') + r"}")
            if item.get('description'):
                lines.append(f": {item.get('description')}")
            lines.append(r"~\href{" + (item.get('url', '#') or '#') + r"}{[Link]}")
    lines.append(r"\end{itemize}")
    lines.append("")
    
    # Contact
    contact = portfolio.contact.content
    lines.append(r"\section*{Contact}")
    if contact.get('github'):
        lines.append(r"\href{" + contact.get('github') + r"}{GitHub}")
    if contact.get('linkedin'):
        lines.append(r"\href{" + contact.get('linkedin') + r"}{LinkedIn}")
    if contact.get('email'):
        lines.append(f"Email: {contact.get('email')}")
    if contact.get('location'):
        lines.append(f"Location: {contact.get('location')}")
    
    lines.append(r"\end{document}")
    
    return "\n".join(lines)