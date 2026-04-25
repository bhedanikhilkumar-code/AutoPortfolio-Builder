from __future__ import annotations

import base64
from typing import Any


def generate_qr_code_data(portfolio_url: str) -> dict[str, str]:
    """Generate QR code data for portfolio."""
    return {
        "data": portfolio_url,
        "type": "url",
        "size": "300x300",
        "format": "png",
    }


def get_qr_code_url(portfolio_url: str, size: int = 300) -> str:
    """Get QR code image URL using public API."""
    import urllib.parse
    encoded_url = urllib.parse.quote(portfolio_url)
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}"


def generate_vcard(portfolio: dict) -> str:
    """Generate vCard for contact sharing."""
    about = portfolio.get("about", {}).get("content", {})
    contact = portfolio.get("contact", {}).get("content", {})
    
    name = about.get("name", "")
    name_parts = name.split() if name else ["Name"]
    
    first_name = name_parts[0] if len(name_parts) > 0 else "Name"
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    
    vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{name}
"""

    if contact.get("email"):
        vcard += f"EMAIL:{contact.get('email')}\n"
    if contact.get("github"):
        vcard += f"URL:{contact.get('github')}\n"
    if contact.get("linkedin"):
        vcard += f"X-SOCIALPROFILE;type=linkedin:{contact.get('linkedin')}\n"
    if contact.get("location"):
        vcard += f"LOCATION:{contact.get('location')}\n"
    
    hero = portfolio.get("hero", {}).get("content", {})
    if hero.get("headline"):
        vcard += f"TITLE:{hero.get('headline')}\n"
    
    vcard += "END:VCARD"
    
    return vcard


def generate_linktree_alternative(portfolio: dict) -> dict[str, Any]:
    """Generate Linktree-style links."""
    contact = portfolio.get("contact", {}).get("content", {})
    
    links = []
    
    if contact.get("github"):
        links.append({
            "platform": "github",
            "url": contact.get("github"),
            "label": "GitHub",
            "icon": "github",
        })
    
    if contact.get("linkedin"):
        links.append({
            "platform": "linkedin",
            "url": contact.get("linkedin"),
            "label": "LinkedIn",
            "icon": "linkedin",
        })
    
    if contact.get("blog"):
        links.append({
            "platform": "blog",
            "url": contact.get("blog"),
            "label": "Blog",
            "icon": "blog",
        })
    
    if contact.get("email"):
        links.append({
            "platform": "email",
            "url": f"mailto:{contact.get('email')}",
            "label": "Email Me",
            "icon": "email",
        })
    
    return {
        "links": links,
        "total_links": len(links),
    }