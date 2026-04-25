from __future__ import annotations

from typing import Any

from app.schemas import PortfolioResponse


def generate_cover_letter(
    portfolio: PortfolioResponse,
    job_description: str | None = None,
    company_name: str = "the hiring team",
    position: str = "the position",
) -> dict[str, str]:
    """Generate a cover letter from portfolio."""
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    contact = portfolio.contact.content
    
    name = about.get("name", "Candidate")
    email = contact.get("email", "")
    
    # Build opening
    opening = f"""Dear {company_name},

I am writing to express my interest in {position}. With a background in {', '.join(skills.get('highlighted', [])[:3] if skills.get('highlighted') else ['software development'])}, I bring a passion for creating impactful solutions and a track record of delivering results.

"""
    
    # Build body
    body = "In my recent work, I have focused on building projects that demonstrate technical proficiency and problem-solving ability. "
    
    items = projects.get("items", [])
    if items:
        body += f"My work on {[item.get('name') for item in items[:2] if isinstance(item, dict)]} showcases my ability to take projects from concept to deployment. "
    
    body += f"\\n\\nMy technical toolkit includes {', '.join(skills.get('highlighted', [])[:6] if skills.get('highlighted') else ['various technologies'])}. I am particularly interested in roles that allow me to apply these skills to challenging problems."
    
    # Add job-specific customization
    if job_description:
        body += f"\\n\\nYour posting mentions looking for someone with experience in relevant technologies. My background aligns well with these requirements, and I am excited about the opportunity to contribute to your team."
    
    # Build closing
    closing = f"""
I would welcome the opportunity to discuss how my background and skills would benefit your team. Thank you for considering my application.

Sincerely,
{name}
{email}
"""
    
    full_letter = opening + body + closing
    
    return {
        "subject": f"Application for {position}",
        "body": full_letter,
        "name": name,
        "email": email,
    }


def generate_cover_letter_formal(
    portfolio: PortfolioResponse,
    company_name: str,
    position: str,
    requirements: list[str] | None = None,
) -> str:
    """Generate a formal cover letter."""
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    contact = portfolio.contact.content
    
    name = about.get("name", "Candidate")
    email = contact.get("email", "")
    
    letter = f"[Your Name]\\n{email}\\n[Phone]\\n[Date]\\n\\n"
    letter += f"Dear Hiring Manager,\\n\\n"
    letter += f"Re: Application for {position}\\n\\n"
    letter += f"I am writing to apply for the {position} position at {company_name}. "
    
    letter += f"With expertise in {', '.join(skills.get('highlighted', [])[:4] if skills.get('highlighted') else ['technology'])} "
    letter += "and a demonstrated ability to deliver projects that meet business objectives, "
    letter += "I believe I am an excellent candidate for this role.\\n\\n"
    
    if requirements:
        letter += "My qualifications match your stated requirements:\\n"
        for req in requirements[:4]:
            letter += f"• {req}\\n"
        letter += "\\n"
    
    items = projects.get("items", [])
    if items:
        letter += f"My portfolio includes {[item.get('name') for item in items[:2] if isinstance(item, dict)]}, "
        letter += "which demonstrate my ability to deliver production-ready solutions.\\n\\n"
    
    letter += f"I am excited about the opportunity to contribute to {company_name} and would welcome the chance to discuss how my background aligns with your needs.\\n\\n"
    letter += "Thank you for your consideration.\\n\\n"
    letter += f"Sincerely,\\n{name}"
    
    return letter


def customize_cover_letter_for_job(
    base_letter: str,
    job_description: str,
) -> dict[str, Any]:
    """Customize cover letter for specific job."""
    # Extract keywords from job description
    keywords = _extract_job_keywords(job_description)
    
    return {
        "original_letter": base_letter,
        "extracted_keywords": keywords,
        "customization_suggestions": [
            f"Include '{kw}' in your cover letter" for kw in keywords[:5]
        ],
        "match_score": len(keywords[:5]) * 20,  # Simplified scoring
    }


def _extract_job_keywords(job_description: str) -> list[str]:
    """Extract key requirements from job description."""
    # Common tech keywords
    common_terms = [
        "python", "javascript", "react", "node", "api", "aws", "docker",
        "kubernetes", "sql", "database", " agile", "scrum", "git",
        "microservices", "cloud", "machine learning", "data",
    ]
    
    desc_lower = job_description.lower()
    found = [term for term in common_terms if term in desc_lower]
    
    return found[:10]