from __future__ import annotations

import re
from typing import Any

from app.schemas import PortfolioResponse


# ATS keywords by role
ATS_KEYWORDS = {
    "frontend": ["javascript", "typescript", "react", "vue", "angular", "css", "html", "ui", "ux", "responsive", "webpack", "node", "ajax", "rest api"],
    "backend": ["python", "java", "node", "golang", "rust", "api", "rest", "graphql", "database", "sql", "nosql", "docker", "kubernetes", "microservices", "aws", "cloud"],
    "fullstack": ["javascript", "typescript", "react", "node", "python", "api", "rest", "database", "sql", "docker", "git", "aws"],
    "data": ["python", "r", "sql", "machine learning", "tensorflow", "pytorch", "pandas", "numpy", "data analysis", "statistics", "visualization", "tableau", "big data"],
    "ai": ["python", "machine learning", "deep learning", "tensorflow", "pytorch", "nlp", "neural network", "ai", "llm", "gpt", "transformer", "computer vision"],
}


def analyze_ats_score(portfolio: PortfolioResponse) -> dict[str, Any]:
    """Analyze portfolio for ATS compatibility."""
    scores: dict[str, Any] = {
        "overall_score": 0,
        "keyword_score": 0,
        "format_score": 0,
        "readability_score": 0,
        "completeness_score": 0,
        "improvements": [],
        "missing_keywords": [],
        "role_scores": {},
    }
    
    # Extract text content
    all_text = _extract_all_text(portfolio)
    
    # 1. Keyword Score (40 points)
    keyword_result = _analyze_keywords(all_text, portfolio)
    scores["keyword_score"] = keyword_result["score"]
    scores["missing_keywords"] = keyword_result["missing"]
    scores["role_scores"] = keyword_result["role_scores"]
    if keyword_result["missing"]:
        scores["improvements"].append(f"Add keywords: {', '.join(keyword_result['missing'][:5])}")
    
    # 2. Format Score (20 points)
    format_result = _analyze_format(portfolio)
    scores["format_score"] = format_result["score"]
    if format_result["issues"]:
        scores["improvements"].extend(format_result["issues"])
    
    # 3. Readability Score (20 points)
    readability_result = _analyze_readability(all_text)
    scores["readability_score"] = readability_result["score"]
    if readability_result["issues"]:
        scores["improvements"].extend(readability_result["issues"])
    
    # 4. Completeness Score (20 points)
    completeness_result = _analyze_completeness(portfolio)
    scores["completeness_score"] = completeness_result["score"]
    if completeness_result["missing"]:
        scores["improvements"].append(f"Add: {', '.join(completeness_result['missing'])}")
    
    # Calculate overall
    scores["overall_score"] = (
        scores["keyword_score"] * 0.4 +
        scores["format_score"] * 0.2 +
        scores["readability_score"] * 0.2 +
        scores["completeness_score"] * 0.2
    )
    
    return scores


def _extract_all_text(portfolio: PortfolioResponse) -> str:
    """Extract all text from portfolio."""
    parts = []
    
    hero = portfolio.hero.content
    parts.append(hero.get("headline", ""))
    parts.append(hero.get("subheadline", ""))
    
    about = portfolio.about.content
    parts.extend(about.get("summary", []))
    if about.get("professional_summary"):
        parts.append(about.get("professional_summary"))
    
    skills = portfolio.skills.content
    parts.extend(skills.get("highlighted", []))
    parts.extend(skills.get("languages", []))
    parts.extend(skills.get("topics", []))
    
    projects = portfolio.projects.content
    for item in projects.get("items", []):
        if isinstance(item, dict):
            parts.append(item.get("name", ""))
            parts.append(item.get("description", ""))
    
    contact = portfolio.contact.content
    parts.extend([v for v in contact.values() if v])
    
    return " ".join([p for p in parts if p]).lower()


def _analyze_keywords(text: str, portfolio: PortfolioResponse) -> dict[str, Any]:
    """Analyze keywords for ATS."""
    # Get target role from profile or infer
    skills = portfolio.skills.content
    languages = [l.lower() for l in skills.get("languages", [])]
    topics = [t.lower() for t in skills.get("topics", [])]
    
    # Determine likely role
    role = _infer_role(languages, topics)
    role_keywords = ATS_KEYWORDS.get(role, ATS_KEYWORDS["fullstack"])
    
    found = []
    missing = []
    role_scores = {}
    
    for keyword in role_keywords:
        if keyword.lower() in text:
            found.append(keyword)
        else:
            missing.append(keyword)
    
    # Score based on keyword match
    if role_keywords:
        match_rate = len(found) / len(role_keywords)
        score = min(100, int(match_rate * 100))
    
    # Calculate scores for all roles
    for r, kwds in ATS_KEYWORDS.items():
        r_found = sum(1 for k in kwds if k.lower() in text)
        role_scores[r] = int((r_found / len(kwds)) * 100) if kwds else 0
    
    return {
        "score": score,
        "found": found,
        "missing": missing,
        "role_scores": role_scores,
    }


def _infer_role(languages: list[str], topics: list[str]) -> str:
    """Infer primary role from skills."""
    text = " ".join(languages + topics).lower()
    
    if any(t in text for t in ["react", "vue", "angular", "css", "ui"]):
        return "frontend"
    if any(t in text for t in ["tensorflow", "pytorch", "machine learning", "nlp"]):
        return "ai"
    if any(t in text for t in ["sql", "pandas", "data", "statistics"]):
        return "data"
    if any(t in text for t in ["docker", "kubernetes", "aws", "api"]):
        return "backend"
    
    return "fullstack"


def _analyze_format(portfolio: PortfolioResponse) -> dict[str, Any]:
    """Analyze resume format."""
    issues = []
    score = 100
    
    # Check for required sections
    required_sections = ["hero", "about", "skills", "projects", "contact"]
    for section in required_sections:
        section_data = getattr(portfolio, section, None)
        if not section_data or not section_data.content:
            issues.append(f"Missing {section} section")
            score -= 15
    
    # Check for contact info
    contact = portfolio.contact.content
    has_contact = any([
        contact.get("github"),
        contact.get("linkedin"),
        contact.get("email"),
    ])
    if not has_contact:
        issues.append("Add contact links")
        score -= 10
    
    return {
        "score": max(0, score),
        "issues": issues,
    }


def _analyze_readability(text: str) -> dict[str, Any]:
    """Analyze readability."""
    issues = []
    score = 80
    
    # Check for common ATS problems
    if re.search(r'[{}]', text):
        issues.append("Avoid special characters {}")
        score -= 10
    
    if len(text) < 200:
        issues.append("Content too short")
        score -= 15
    
    # Check for proper sentences
    sentences = re.findall(r'[.!?]', text)
    if len(sentences) < 3:
        issues.append("Add more complete sentences")
        score -= 10
    
    return {
        "score": max(0, score),
        "issues": issues,
    }


def _analyze_completeness(portfolio: PortfolioResponse) -> dict[str, Any]:
    """Analyze portfolio completeness."""
    missing = []
    score = 50
    
    # Check key fields
    contact = portfolio.contact.content
    about = portfolio.about.content
    projects = portfolio.projects.content
    skills = portfolio.skills.content
    
    if contact.get("github"):
        score += 10
    else:
        missing.append("GitHub link")
    
    if contact.get("linkedin"):
        score += 10
    else:
        missing.append("LinkedIn link")
    
    if about.get("name"):
        score += 10
    else:
        missing.append("name")
    
    if about.get("summary"):
        score += 10
    else:
        missing.append("about summary")
    
    if projects.get("items"):
        score += 10
    else:
        missing.append("projects")
    
    return {
        "score": min(100, score),
        "missing": missing,
    }


def get_role_recommendations(portfolio: PortfolioResponse) -> dict[str, Any]:
    """Get role-specific recommendations."""
    all_text = _extract_all_text(portfolio)
    skills = portfolio.skills.content
    languages = [l.lower() for l in skills.get("languages", [])]
    topics = [t.lower() for t in skills.get("topics", [])]
    
    role_scores = {}
    for role, keywords in ATS_KEYWORDS.items():
        found = sum(1 for k in keywords if k.lower() in all_text)
        role_scores[role] = {
            "match": found,
            "total": len(keywords),
            "percentage": int((found / len(keywords)) * 100) if keywords else 0,
        }
    
    best_role = max(role_scores.items(), key=lambda x: x[1]["percentage"])
    recommended = best_role[0] if best_role[1]["percentage"] > 20 else "fullstack"
    
    return {
        "recommended_role": recommended,
        "role_scores": role_scores,
    }