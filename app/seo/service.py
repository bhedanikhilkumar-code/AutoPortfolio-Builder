from __future__ import annotations

import json
import re
from typing import Any

from app.schemas import PortfolioResponse


def generate_meta_tags(portfolio: PortfolioResponse) -> dict[str, str]:
    """Generate SEO meta tags."""
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    contact = portfolio.contact.content
    
    name = about.get("name", "")
    title = hero.get("headline", "")
    description = " | ".join(about.get("summary", [])[:2]) if about.get("summary") else title
    
    keywords = []
    keywords.extend(skills.get("highlighted", [])[:8])
    keywords.extend(skills.get("languages", [])[:5])
    
    return {
        "title": f"{name} - {title}" if name else title,
        "description": description[:160] if len(description) > 160 else description,
        "keywords": ", ".join(keywords[:10]),
        "author": name,
        "og:title": f"{name} - {title}" if name else title,
        "og:description": description[:200] if len(description) > 200 else description,
        "og:type": "profile",
    }


def generate_opengraph_tags(portfolio: PortfolioResponse) -> str:
    """Generate OpenGraph meta tags HTML."""
    meta = generate_meta_tags(portfolio)
    about = portfolio.about.content
    
    tags = []
    tags.append(f'<meta property="og:title" content="{_escape_html(meta["og:title"])}">')
    tags.append(f'<meta property="og:description" content="{_escape_html(meta["og:description"])}">')
    tags.append('<meta property="og:type" content="profile">')
    
    if contact := portfolio.contact.content:
        if contact.get("github"):
            tags.append(f'<meta property="og:url" content="{_escape_html(contact.get("github"))}">')
    
    if about.get("avatar_url"):
        tags.append(f'<meta property="og:image" content="{_escape_html(about.get("avatar_url"))}">')
    
    return "\n".join(tags)


def generate_jsonld(portfolio: PortfolioResponse) -> str:
    """Generate JSON-LD schema for portfolio."""
    about = portfolio.about.content
    hero = portfolio.hero.content
    skills = portfolio.skills.content
    contact = portfolio.contact.content
    
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": about.get("name", ""),
        "url": contact.get("github", ""),
        "jobTitle": hero.get("headline", ""),
    }
    
    same_as = []
    if contact.get("github"):
        same_as.append(contact.get("github"))
    if contact.get("linkedin"):
        same_as.append(contact.get("linkedin"))
    if same_as:
        schema["sameAs"] = same_as
    
    knows_about = skills.get("highlighted", [])[:10]
    if knows_about:
        schema["knowsAbout"] = knows_about
    
    return json.dumps(schema, indent=2)


def generate_twitter_card(portfolio: PortfolioResponse) -> str:
    """Generate Twitter Card meta tags."""
    about = portfolio.about.content
    hero = portfolio.hero.content
    
    name = about.get("name", "")
    description = " | ".join(about.get("summary", [])[:1])
    
    tags = []
    tags.append('<meta name="twitter:card" content="summary_large_image">')
    tags.append(f'<meta name="twitter:title" content="{_escape_html(name or hero.get("headline", ""))}">')
    tags.append(f'<meta name="twitter:description" content="{_escape_html(description[:200])}">')
    
    if about.get("avatar_url"):
        tags.append(f'<meta name="twitter:image" content="{_escape_html(about.get("avatar_url"))}">')
    
    return "\n".join(tags)


def analyze_seo_score(portfolio: PortfolioResponse) -> dict[str, Any]:
    """Analyze SEO score and provide improvements."""
    score = 0
    improvements = []
    
    about = portfolio.about.content
    hero = portfolio.hero.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    contact = portfolio.contact.content
    
    if hero.get("headline"):
        score += 20
    else:
        improvements.append("Add headline")
    
    if about.get("summary"):
        score += 20
    else:
        improvements.append("Add about summary")
    
    if skills.get("highlighted"):
        score += 15
    else:
        improvements.append("Add skills")
    
    if projects.get("items"):
        score += 15
    else:
        improvements.append("Add projects")
    
    if contact.get("github"):
        score += 10
    else:
        improvements.append("Add GitHub link")
    
    if contact.get("location"):
        score += 5
    else:
        improvements.append("Add location")
    
    if about.get("avatar_url"):
        score += 5
    else:
        improvements.append("Add profile photo")
    
    if contact.get("linkedin"):
        score += 5
    else:
        improvements.append("Add LinkedIn")
    
    if contact.get("blog"):
        score += 5
    else:
        improvements.append("Add blog")
    
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D" if score >= 50 else "F"
    
    return {"score": score, "grade": grade, "improvements": improvements}


def _escape_html(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")


def inject_seo_tags(html: str, portfolio: PortfolioResponse) -> str:
    """Inject all SEO tags into HTML."""
    meta = generate_meta_tags(portfolio)
    og_tags = generate_opengraph_tags(portfolio)
    twitter_tags = generate_twitter_card(portfolio)
    jsonld = generate_jsonld(portfolio)
    
    seo = "<!-- SEO -->\n"
    seo += f'<meta name="description" content="{_escape_html(meta["description"])}">\n'
    seo += f'<meta name="keywords" content="{_escape_html(meta["keywords"])}">\n'
    seo += og_tags + "\n" + twitter_tags + "\n"
    seo += f'<script type="application/ld+json">{jsonld}</script>'
    
    if "</head>" in html:
        return html.replace("</head>", seo + "</head>")
    elif "<body" in html:
        return html.replace("<body", "<body>" + seo)
    return seo + html


def generate_all_social_meta(portfolio: PortfolioResponse) -> dict[str, str]:
    """Generate all social meta tags as dict."""
    meta = generate_meta_tags(portfolio)
    about = portfolio.about.content
    
    return {
        "description": meta["description"],
        "keywords": meta["keywords"],
        "og:title": meta["og:title"],
        "og:description": meta["og:description"],
        "og:type": "profile",
        "twitter:card": "summary_large_image",
        "og:image": about.get("avatar_url", ""),
    }