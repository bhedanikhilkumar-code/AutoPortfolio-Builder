from __future__ import annotations

from typing import Any

from app.schemas import PortfolioResponse


def generate_interview_questions(portfolio: PortfolioResponse, role: str = "general") -> dict[str, Any]:
    """Generate interview questions based on portfolio."""
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    contact = portfolio.contact.content
    
    questions = []
    
    # General questions
    questions.extend([
        "Tell me about yourself.",
        "What interests you about this role?",
        "Where do you see yourself in 5 years?",
    ])
    
    # Skills-based questions
    highlighted = skills.get("highlighted", [])[:5]
    for skill in highlighted:
        questions.append(f"Tell me about your experience with {skill}.")
        questions.append(f"How would you rate your proficiency in {skill}?")
    
    # Project-based questions
    items = projects.get("items", [])[:3]
    for item in items:
        if isinstance(item, dict):
            questions.append(f"Walk me through {item.get('name', 'your project')}.")
            questions.append(f"What challenges did you face in {item.get('name', 'your project')}?")
            if item.get("stars"):
                questions.append(f"How did you grow {item.get('name')} to {item.get('stars')} stars?")
    
    # Behavioral questions
    questions.extend([
        "Tell me about a time you solved a difficult problem.",
        "Describe a project you're most proud of.",
        "How do you stay updated with technology?",
    ])
    
    # Role-specific questions
    if role in ["frontend", "fullstack"]:
        questions.extend([
            "Explain your approach to responsive design.",
            "How do you optimize web performance?",
        ])
    
    if role in ["backend", "fullstack"]:
        questions.extend([
            "Describe your API design principles.",
            "How do you handle database scalability?",
        ])
    
    if role == "data":
        questions.extend([
            "Walk me through your data analysis process.",
            "How do you ensure data quality?",
        ])
    
    return {
        "questions": questions[:20],
        "count": len(questions[:20]),
        "estimated_duration_minutes": len(questions[:20]) * 3,
    }


def generate_mock_interview(
    portfolio: PortfolioResponse,
    num_questions: int = 5,
) -> list[dict[str, str]]:
    """Generate a mock interview session."""
    generated = generate_interview_questions(portfolio)
    all_qs = generated["questions"]
    
    mock_interview = []
    for i, q in enumerate(all_qs[:num_questions]):
        mock_interview.append({
            "number": i + 1,
            "question": q,
            "type": _classify_question(q),
            "time_suggested": "2-3 minutes",
        })
    
    return mock_interview


def _classify_question(question: str) -> str:
    """Classify question type."""
    q_lower = question.lower()
    
    if any(w in q_lower for w in ["tell me about", "walk me", "describe"]):
        return "behavioral"
    elif any(w in q_lower for w in ["how would you", "how do you", "what is"]):
        return "technical"
    elif any(w in q_lower for w in ["where", "what", "why"]):
        return "situational"
    else:
        return "general"


def generate_answer_suggestions(
    portfolio: PortfolioResponse,
    question: str,
) -> list[str]:
    """Generate answer suggestions for a question."""
    hero = portfolio.hero.content
    about = portfolio.about.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    
    suggestions = []
    q_lower = question.lower()
    
    if "yourself" in q_lower:
        suggestions.append(f"I am {about.get('name', 'a developer')} focused on {', '.join(skills.get('highlighted', [])[:3])}.")
    
    if "project" in q_lower or "proud" in q_lower:
        items = projects.get("items", [])
        if items:
            top = items[0]
            if isinstance(top, dict):
                suggestions.append(f"My most fulfilling project was {top.get('name')}: {top.get('description', 'an impactful solution')}.")
    
    if any(s in q_lower for s in ["experience", "skill", "proficient"]):
        suggestions.append(", ".join(skills.get("highlighted", [])[:5]))
    
    if "challenge" in q_lower or "problem" in q_lower:
        suggestions.append("I approach challenges systematically - first understanding the problem, then researching solutions, and iterating based on feedback.")
    
    if "updated" in q_lower or "stay current" in q_lower:
        suggestions.append("I follow tech blogs, contribute to open source, and regularly experiment with new technologies in personal projects.")
    
    if not suggestions:
        suggestions.append("Based on your portfolio, highlight your key achievements and connect them to the role's requirements.")
    
    return suggestions