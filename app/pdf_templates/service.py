from __future__ import annotations

from io import BytesIO
from typing import Any

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

from app.schemas import PortfolioResponse


TEMPLATES = {
    "modern": {
        "name": "Modern",
        "primary_color": (37, 99, 235),  # Blue
        "font_family": "Helvetica",
        "header_style": "bold",
        "layout": "single_column",
    },
    "classic": {
        "name": "Classic",
        "primary_color": (0, 0, 0),  # Black
        "font_family": "Times",
        "header_style": "underline",
        "layout": "two_column",
    },
    "minimal": {
        "name": "Minimal",
        "primary_color": (50, 50, 50),  # Dark Gray
        "font_family": "Helvetica",
        "header_style": "simple",
        "layout": "single_column",
    },
    "creative": {
        "name": "Creative",
        "primary_color": (139, 92, 246),  # Purple
        "font_family": "Helvetica",
        "header_style": "colored",
        "layout": "mixed",
    },
    "executive": {
        "name": "Executive",
        "primary_color": (30, 58, 138),  # Navy
        "font_family": "Times",
        "header_style": "bold",
        "layout": "two_column",
    },
    "gradient": {
        "name": "Gradient",
        "primary_color": (6, 182, 212),  # Cyan
        "font_family": "Helvetica",
        "header_style": "gradient",
        "layout": "single_column",
    },
}


def render_pdf_template(
    portfolio: PortfolioResponse,
    template: str = "modern",
    include_seo: bool = True,
) -> bytes:
    """Render portfolio as PDF with template."""
    if FPDF is None:
        raise ImportError("FPDF not installed. Run: pip install fpdf2")
    
    template_config = TEMPLATES.get(template, TEMPLATES["modern"])
    
    if template_config["layout"] == "two_column":
        return _render_two_column_pdf(portfolio, template_config)
    else:
        return _render_single_column_pdf(portfolio, template_config)


def _render_single_column_pdf(portfolio: PortfolioResponse, config: dict) -> bytes:
    """Render single column PDF."""
    pdf = FPDF()
    pdf.add_page()
    
    primary = config["primary_color"]
    primary_hex = f"#{primary[0]:02x}{primary[1]:02x}{primary[2]:02x}"
    
    # Header
    about = portfolio.about.content
    hero = portfolio.hero.content
    
    # Name
    name = about.get("name", "Portfolio")
    pdf.set_font(config["font_family"], "B", 24)
    pdf.set_text_color(*primary)
    pdf.cell(0, 15, name.encode("latin-1", "replace").decode("latin-1"), ln=True, align="C")
    
    # Headline
    pdf.set_font(config["font_family"], "", 12)
    pdf.set_text_color(100, 100, 100)
    headline = hero.get("headline", "")
    pdf.multi_cell(0, 6, headline.encode("latin-1", "replace").decode("latin-1"), align="C")
    
    pdf.ln(5)
    
    # Contact line
    contact = portfolio.contact.content
    pdf.set_font(config["font_family"], "I", 10)
    pdf.set_text_color(150, 150, 150)
    contact_parts = []
    if contact.get("github"):
        contact_parts.append(contact.get("github"))
    if contact.get("email"):
        contact_parts.append(contact.get("email"))
    if contact.get("location"):
        contact_parts.append(contact.get("location"))
    if contact_parts:
        pdf.cell(0, 5, " | ".join(contact_parts), ln=True, align="C")
    
    pdf.ln(8)
    
    # About section
    pdf.set_font(config["font_family"], "B", 14)
    pdf.set_text_color(*primary)
    pdf.cell(0, 8, "About", ln=True)
    
    pdf.set_font(config["font_family"], "", 11)
    pdf.set_text_color(50, 50, 50)
    for point in about.get("summary", []):
        pdf.multi_cell(0, 5, f"• {point}")
    pdf.ln(3)
    
    # Skills section
    skills = portfolio.skills.content
    if skills.get("highlighted"):
        pdf.set_font(config["font_family"], "B", 14)
        pdf.set_text_color(*primary)
        pdf.cell(0, 8, "Skills", ln=True)
        
        pdf.set_font(config["font_family"], "", 11)
        pdf.set_text_color(50, 50, 50)
        skills_text = ", ".join(str(s) for s in skills.get("highlighted", [])[:10])
        pdf.multi_cell(0, 5, skills_text)
        pdf.ln(3)
    
    # Projects section
    projects = portfolio.projects.content
    if projects.get("items"):
        pdf.set_font(config["font_family"], "B", 14)
        pdf.set_text_color(*primary)
        pdf.cell(0, 8, "Projects", ln=True)
        
        for item in projects.get("items", [])[:6]:
            if isinstance(item, dict):
                pdf.set_font(config["font_family"], "B", 12)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 6, item.get("name", "Untitled"), ln=True)
                
                if item.get("description"):
                    pdf.set_font(config["font_family"], "", 10)
                    pdf.set_text_color(100, 100, 100)
                    pdf.multi_cell(0, 5, item.get("description", ""))
                
                meta_parts = []
                if item.get("language"):
                    meta_parts.append(item.get("language"))
                if item.get("stars"):
                    meta_parts.append(f"⭐ {item.get('stars')}")
                if item.get("url"):
                    meta_parts.append(item.get("url"))
                if meta_parts:
                    pdf.set_font(config["font_family"], "I", 9)
                    pdf.set_text_color(150, 150, 150)
                    pdf.cell(0, 5, " | ".join(str(p) for p in meta_parts), ln=True)
                
                pdf.ln(3)
    
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def _render_two_column_pdf(portfolio: PortfolioResponse, config: dict) -> bytes:
    """Render two column PDF (classic layout)."""
    pdf = FPDF()
    pdf.add_page()
    
    primary = config["primary_color"]
    
    # Header
    about = portfolio.about.content
    hero = portfolio.hero.content
    contact = portfolio.contact.content
    skills = portfolio.skills.content
    projects = portfolio.projects.content
    
    # Left column width
    left_w = 65
    right_w = 125
    margin = 10
    
    # Name
    pdf.set_font(config["font_family"], "B", 22)
    pdf.set_text_color(*primary)
    pdf.cell(0, 12, about.get("name", "Portfolio"), ln=True, align="C")
    
    # Title
    pdf.set_font(config["font_family"], "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, hero.get("headline", ""), ln=True, align="C")
    pdf.ln(5)
    
    # Contact info
    pdf.set_font(config["font_family"], "", 10)
    contact_info = []
    if contact.get("email"):
        contact_info.append(contact.get("email"))
    if contact.get("github"):
        contact_info.append("GitHub: " + contact.get("github").split("/")[-1])
    if contact.get("location"):
        contact_info.append(contact.get("location"))
    if contact_info:
        pdf.cell(0, 5, " | ".join(contact_info), ln=True, align="C")
    
    pdf.ln(8)
    
    # Two columns
    col_y_start = pdf.get_y()
    
    # Left column - Summary & Skills
    pdf.set_x(margin)
    
    # Summary
    pdf.set_font(config["font_family"], "B", 13)
    pdf.set_text_color(*primary)
    pdf.cell(left_w, 7, "Summary", ln=True)
    
    pdf.set_font(config["font_family"], "", 10)
    pdf.set_text_color(50, 50, 50)
    for point in about.get("summary", [])[:5]:
        pdf.multi_cell(left_w, 5, f"• {point}")
    pdf.ln(3)
    
    # Skills
    if skills.get("highlighted"):
        pdf.set_font(config["font_family"], "B", 13)
        pdf.set_text_color(*primary)
        pdf.cell(left_w, 7, "Skills", ln=True)
        
        pdf.set_font(config["font_family"], "", 10)
        pdf.set_text_color(50, 50, 50)
        for skill in skills.get("highlighted", [])[:12]:
            pdf.multi_cell(left_w, 5, f"• {skill}")
    
    # Right column - Projects
    pdf.set_xy(margin + left_w + 5, col_y_start)
    
    pdf.set_font(config["font_family"], "B", 13)
    pdf.set_text_color(*primary)
    pdf.cell(right_w, 7, "Projects", ln=True)
    
    for item in projects.get("items", [])[:6]:
        if isinstance(item, dict):
            pdf.set_xy(margin + left_w + 5, pdf.get_y())
            
            pdf.set_font(config["font_family"], "B", 11)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(right_w, 5, item.get("name", ""))
            
            if item.get("description"):
                pdf.set_xy(margin + left_w + 5, pdf.get_y())
                pdf.set_font(config["font_family"], "", 9)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(right_w, 5, item.get("description", ""))
            
            pdf.ln(2)
    
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def list_pdf_templates() -> list[dict[str, Any]]:
    """List all available PDF templates."""
    return [
        {"id": k, "name": v["name"], "layout": v["layout"]}
        for k, v in TEMPLATES.items()
    ]


def get_template_config(template_id: str) -> dict[str, Any]:
    """Get template configuration."""
    return TEMPLATES.get(template_id, TEMPLATES["modern"])