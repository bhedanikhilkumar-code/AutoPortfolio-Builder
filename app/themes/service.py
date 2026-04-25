from __future__ import annotations

from typing import Any


# Built-in themes
THEMES = {
    "modern": {
        "name": "Modern",
        "primary": "#2563eb",
        "secondary": "#64748b",
        "background": "#ffffff",
        "text": "#1e293b",
        "accent": "#3b82f6",
    },
    "dark": {
        "name": "Dark Mode",
        "primary": "#3b82f6",
        "secondary": "#94a3b8",
        "background": "#0f172a",
        "text": "#f1f5f9",
        "accent": "#60a5fa",
    },
    "midnight": {
        "name": "Midnight",
        "primary": "#8b5cf6",
        "secondary": "#a78bfa",
        "background": "#0c0a1d",
        "text": "#e2e8f0",
        "accent": "#a78bfa",
    },
    "forest": {
        "name": "Forest",
        "primary": "#22c55e",
        "secondary": "#86efac",
        "background": "#052e16",
        "text": "#f0fdf4",
        "accent": "#4ade80",
    },
    "sunset": {
        "name": "Sunset",
        "primary": "#f97316",
        "secondary": "#fdba74",
        "background": "#1c1917",
        "text": "#fff7ed",
        "accent": "#fb923c",
    },
    "ocean": {
        "name": "Ocean",
        "primary": "#06b6d4",
        "secondary": "#67e8f9",
        "background": "#083344",
        "text": "#ecfeff",
        "accent": "#22d3ee",
    },
    "rose": {
        "name": "Rose",
        "primary": "#f43f5e",
        "secondary": "#fb7185",
        "background": "#1c1917",
        "text": "#fff1f2",
        "accent": "#fb7185",
    },
    "minimal": {
        "name": "Minimal",
        "primary": "#000000",
        "secondary": "#6b7280",
        "background": "#ffffff",
        "text": "#111827",
        "accent": "#374151",
    },
}


def get_theme(theme_id: str) -> dict[str, str]:
    """Get theme by ID."""
    return THEMES.get(theme_id, THEMES["modern"])


def list_themes() -> dict[str, str]:
    """List all available themes."""
    return {k: v["name"] for k, v in THEMES.items()}


def generate_custom_css(
    theme_id: str,
    custom_css: str | None = None,
    font_family: str = "Inter",
) -> str:
    """Generate CSS with theme variables."""
    theme = get_theme(theme_id)
    
    css = ":root {\n"
    css += f"  --primary: {theme['primary']};\n"
    css += f"  --secondary: {theme['secondary']};\n"
    css += f"  --background: {theme['background']};\n"
    css += f"  --text: {theme['text']};\n"
    css += f"  --accent: {theme['accent']};\n"
    css += f"  --font-family: '{font_family}', sans-serif;\n"
    css += "}\n\n"
    css += "body {\n  background: var(--background);\n  color: var(--text);\n  font-family: var(--font-family);\n}\n\n"
    css += ".hero { color: var(--primary); }\n"
    css += ".btn { background: var(--primary); color: white; }\n"
    css += ".card { border-color: var(--secondary); }\n"
    
    # Add custom CSS
    if custom_css:
        css += f"\n/* Custom CSS */\n{custom_css}"
    
    return css


def inject_theme(html: str, theme_id: str, custom_css: str | None = None) -> str:
    """Inject theme into HTML page."""
    css = generate_custom_css(theme_id, custom_css)
    css_tag = f'<style>{css}</style>'
    
    # Inject before </head> or at start of <body>
    if "</head>" in html:
        return html.replace("</head>", f"{css_tag}</head>")
    elif "<body" in html:
        return html.replace("<body", f"<body>{css_tag}")
    return css_tag + html