from __future__ import annotations

from typing import Any

from app.schemas import PortfolioResponse, RepoSummary


def reorder_projects(
    portfolio: PortfolioResponse,
    new_order: list[str],
) -> PortfolioResponse:
    """Reorder projects based on new_order list of project names."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    if not items:
        return portfolio
    
    # Create index for fast lookup
    item_map: dict[str, dict] = {}
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            item_map[item["name"]] = item
    
    # Reorder items based on new_order
    reordered = []
    for name in new_order:
        if name in item_map:
            reordered.append(item_map[name])
    
    # Add any items not in new_order at the end
    for item in items:
        if isinstance(item, dict) and item.get("name") and item["name"] not in new_order:
            reordered.append(item)
    
    # Update portfolio
    new_portfolio = portfolio.model_copy(deep=True)
    new_portfolio.projects.content["items"] = reordered
    
    return new_portfolio


def sort_projects_by_stars(
    portfolio: PortfolioResponse,
    descending: bool = True,
) -> PortfolioResponse:
    """Sort projects by star count."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    if not items:
        return portfolio
    
    def get_stars(item):
        if isinstance(item, dict):
            return item.get("stargazers_count", 0)
        return 0
    
    sorted_items = sorted(
        [i for i in items if isinstance(i, dict)],
        key=get_stars,
        reverse=descending,
    )
    
    new_portfolio = portfolio.model_copy(deep=True)
    new_portfolio.projects.content["items"] = sorted_items
    
    return new_portfolio


def sort_projects_by_name(
    portfolio: PortfolioResponse,
    descending: bool = False,
) -> PortfolioResponse:
    """Sort projects alphabetically."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    if not items:
        return portfolio
    
    sorted_items = sorted(
        [i for i in items if isinstance(i, dict)],
        key=lambda x: x.get("name", "").lower(),
        reverse=descending,
    )
    
    new_portfolio = portfolio.model_copy(deep=True)
    new_portfolio.projects.content["items"] = sorted_items
    
    return new_portfolio


def filter_projects_by_language(
    portfolio: PortfolioResponse,
    language: str,
) -> PortfolioResponse:
    """Filter projects by programming language."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    if not items:
        return portfolio
    
    filtered = [
        item for item in items
        if isinstance(item, dict) and item.get("language", "").lower() == language.lower()
    ]
    
    new_portfolio = portfolio.model_copy(deep=True)
    new_portfolio.projects.content["items"] = filtered
    
    return new_portfolio


def remove_project(
    portfolio: PortfolioResponse,
    project_name: str,
) -> PortfolioResponse:
    """Remove a project by name."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    if not items:
        return portfolio
    
    filtered = [
        item for item in items
        if not (isinstance(item, dict) and item.get("name") == project_name)
    ]
    
    new_portfolio = portfolio.model_copy(deep=True)
    new_portfolio.projects.content["items"] = filtered
    
    return new_portfolio


def add_project(
    portfolio: PortfolioResponse,
    project: dict,
) -> PortfolioResponse:
    """Add a new project to portfolio."""
    new_portfolio = portfolio.model_copy(deep=True)
    
    items = new_portfolio.projects.content.get("items", [])
    items.append(project)
    new_portfolio.projects.content["items"] = items
    
    return new_portfolio


def update_project(
    portfolio: PortfolioResponse,
    project_name: str,
    updates: dict,
) -> PortfolioResponse:
    """Update project details."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    new_portfolio = portfolio.model_copy(deep=True)
    new_items = []
    
    for item in items:
        if isinstance(item, dict) and item.get("name") == project_name:
            new_items.append({**item, **updates})
        else:
            new_items.append(item)
    
    new_portfolio.projects.content["items"] = new_items
    
    return new_portfolio


def get_projects_summary(portfolio: PortfolioResponse) -> dict[str, Any]:
    """Get projects summary/analytics."""
    projects_data = portfolio.projects.content
    items = projects_data.get("items", [])
    
    total_stars = sum(i.get("stargazers_count", 0) for i in items if isinstance(i, dict))
    total_forks = sum(i.get("forks_count", 0) for i in items if isinstance(i, dict))
    
    languages = {}
    for item in items:
        if isinstance(item, dict) and item.get("language"):
            lang = item.get("language")
            languages[lang] = languages.get(lang, 0) + 1
    
    return {
        "total_projects": len(items),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "languages": languages,
        "most_starred": max(
            [(i.get("name", ""), i.get("stargazers_count", 0)) for i in items if isinstance(i, dict)],
            key=lambda x: x[1],
            default=("", 0),
        )[0],
    }