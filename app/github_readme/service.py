from __future__ import annotations

from typing import Any

from app.schemas import PortfolioResponse


def generate_github_readme(portfolio: PortfolioResponse) -> str:
    """Generate GitHub profile README."""
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    contact = portfolio.contact.content
    
    name = about.get("name", "Developer")
    headline = hero.get("headline", "")
    
    readme = f"""# 👋 Hi, I'm {name}

{headline}

![Profile Views](https://komarev.com/ghprofile/?username=YOUR_USERNAME&style=flat-square)
![GitHub Followers](https://img.shields.io/github/followers/YOUR_USERNAME?style=social)
![Stars](https://img.shields.io/github/stars/YOUR_USERNAME?style=social)

## 🛠️ Tech Stack

"""
    
    # Add skills
    highlighted = skills.get("highlighted", [])
    if highlighted:
        readme += "| "
        readme += " | ".join(str(s) for s in highlighted[:8])
        readme += " |\n"
    
    readme += "\n## 📂 Top Projects\n\n"
    
    items = projects.get("items", [])[:5]
    for item in items:
        if isinstance(item, dict):
            stars = "⭐" * min(int(item.get("stargazers_count", 0) / 10), 5) if item.get("stargazers_count") else ""
            readme += f"- [{item.get('name')}]({item.get('html_url', '#')}) - {item.get('description', 'No description')}"
            if stars:
                readme += f" {stars}"
            readme += "\n"
    
    readme += "\n## 📊 Stats\n\n"
    readme += f"""![GitHub Stats](https://github-readme-stats.vercel.app/api?username=YOUR_USERNAME&theme=transparent&hide_border=true)
![Top Langs](https://github-readme-stats.vercel.app/api/top-langs/?username=YOUR_USERNAME&theme=transparent&hide_border=true)

## 📫 Connect

"""
    
    if contact.get("github"):
        readme += f"- [GitHub]({contact.get('github')})"
    if contact.get("linkedin"):
        readme += f" | [LinkedIn]({contact.get('linkedin')})"
    if contact.get("email"):
        readme += f" | {contact.get('email')}"
    if contact.get("blog"):
        readme += f" | [Blog]({contact.get('blog')})"
    
    readme += "\n\n---\n*Generated with [AutoPortfolio Builder](https://github.com/bhedanikhilkumar-code/AutoPortfolio-Builder)*\n"
    
    return readme


def generate_streak_stats_widget() -> str:
    """Generate GitHub streak stats widget."""
    return """
<!-- GitHub Streak Stats -->
<p align="center">
  <a href="https://streak-stats.demolab.com/?user=YOUR_USERNAME" title="GitHub Streak">
    <img src="https://streak-stats.demolab.com/?user=YOUR_USERNAME&theme=default&hide_border=true"/>
  </a>
</p>
"""


def generate_activity_graph_widget() -> str:
    """Generate GitHub activity graph."""
    return """
<!-- GitHub Activity Graph -->
<img src="https://activity-graph.herokuapp.com/graph?username=YOUR_USERNAME&theme=github">
"""


def get_readme_sections() -> list[dict[str, str]]:
    """Get available README sections."""
    return [
        {"id": "header", "name": "Header", "description": "Name and tagline"},
        {"id": "stats", "name": "Stats", "description": "Profile views, followers, stars badges"},
        {"id": "skills", "name": "Tech Stack", "description": "Skills/tools grid"},
        {"id": "projects", "name": "Projects", "description": "Top repositories"},
        {"id": "github_stats", "name": "GitHub Stats", "description": "Contribution stats"},
        {"id": "contact", "name": "Contact", "description": "Social links"},
        {"id": "streak", "name": "Streak", "description": "GitHub streak widget"},
        {"id": "activity", "name": "Activity Graph", "description": "Activity visualization"},
    ]