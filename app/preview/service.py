from __future__ import annotations

import hashlib
import secrets
from typing import Any

from app.schemas import PortfolioResponse
from app.services.portfolio import render_portfolio_html
from app.themes.service import get_theme, generate_custom_css
from app.seo.service import inject_seo_tags


# Preview sessions storage
PREVIEW_SESSIONS: dict[str, dict[str, Any]] = {}


def create_preview_session(
    portfolio: PortfolioResponse,
    theme_id: str = "modern",
    custom_css: str | None = None,
) -> tuple[str, str]:
    """Create a preview session. Returns (session_id, preview_url)."""
    session_id = secrets.token_urlsafe(8)
    preview_key = secrets.token_urlsafe(12)
    
    PREVIEW_SESSIONS[session_id] = {
        "portfolio": portfolio,
        "theme_id": theme_id,
        "custom_css": custom_css,
        "preview_key": hashlib.sha256(preview_key.encode()).hexdigest(),
        "created_at": secrets.compare_digest.__code__.co_consts[0] if hasattr(secrets, 'compare_digest') else None,
    }
    
    return session_id, preview_key


def get_preview_html(
    portfolio: PortfolioResponse,
    theme_id: str = "modern",
    inject_seo: bool = False,
) -> str:
    """Generate preview HTML with theme."""
    # Render base HTML
    html = render_portfolio_html(portfolio)
    
    # Generate theme CSS
    theme_css = generate_custom_css(theme_id)
    
    # Inject theme into HTML
    if theme_id != "minimal":
        styled_html = _apply_theme(html, theme_css)
    else:
        styled_html = html
    
    # Optionally inject SEO
    if inject_seo:
        styled_html = inject_seo_tags(styled_html, portfolio)
    
    return styled_html


def _apply_theme(html: str, theme_css: str) -> str:
    """Apply theme CSS to HTML."""
    style_tag = f"<style>{theme_css}</style>"
    
    if "</head>" in html:
        return html.replace("</head>", style_tag + "</head>")
    elif "<body>" in html:
        return html.replace("<body>", f"<body>{style_tag}")
    elif "<body" in html:
        return html.replace("<body", f"<body>{style_tag}")
    
    return style_tag + html


def get_preview_url(base_url: str, session_id: str, key: str) -> str:
    """Get preview URL with auth key."""
    return f"{base_url}/preview/{session_id}?key={key}"


def validate_preview_key(session_id: str, key: str) -> bool:
    """Validate preview key."""
    if session_id not in PREVIEW_SESSIONS:
        return False
    
    session = PREVIEW_SESSIONS[session_id]
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    return session.get("preview_key") == key_hash


def get_preview_portfolio(session_id: str) -> PortfolioResponse | None:
    """Get portfolio from preview session."""
    return PREVIEW_SESSIONS.get(session_id, {}).get("portfolio")


def delete_preview_session(session_id: str) -> bool:
    """Delete preview session."""
    if session_id in PREVIEW_SESSIONS:
        del PREVIEW_SESSIONS[session_id]
        return True
    return False


def generate_shareable_link(
    base_url: str,
    portfolio: PortfolioResponse,
    expires_hours: int = 24,
) -> str:
    """Generate a shareable preview link."""
    share_id = secrets.token_urlsafe(6)
    
    # Store temporarily
    PREVIEW_SESSIONS[share_id] = {
        "portfolio": portfolio,
        "expires_hours": expires_hours,
    }
    
    return f"{base_url}/share/{share_id}"


def get_multi_theme_preview(
    portfolio: PortfolioResponse,
    theme_ids: list[str],
) -> dict[str, str]:
    """Generate previews for multiple themes."""
    previews = {}
    
    for theme_id in theme_ids:
        if theme_id in ["modern", "dark", "midnight", "forest", "ocean", "sunset", "rose", "minimal"]:
            html = get_preview_html(portfolio, theme_id)
            previews[theme_id] = html
    
    return previews