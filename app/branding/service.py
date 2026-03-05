from __future__ import annotations

from app.core.db import get_connection
from app.schemas import BrandingSettingsRequest, BrandingSettingsResponse


def get_branding(user_id: int) -> BrandingSettingsResponse:
    conn = get_connection()
    try:
        row = conn.execute("SELECT palette, font_family, logo_url FROM branding_settings WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return BrandingSettingsResponse(palette="default", font_family="Inter", logo_url=None)
        return BrandingSettingsResponse(palette=row["palette"], font_family=row["font_family"], logo_url=row["logo_url"])
    finally:
        conn.close()


def upsert_branding(user_id: int, payload: BrandingSettingsRequest) -> BrandingSettingsResponse:
    conn = get_connection()
    try:
        exists = conn.execute("SELECT id FROM branding_settings WHERE user_id = ?", (user_id,)).fetchone()
        if exists:
            conn.execute(
                "UPDATE branding_settings SET palette = ?, font_family = ?, logo_url = ?, updated_at = datetime('now') WHERE user_id = ?",
                (payload.palette, payload.font_family, payload.logo_url, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO branding_settings(user_id, palette, font_family, logo_url) VALUES(?, ?, ?, ?)",
                (user_id, payload.palette, payload.font_family, payload.logo_url),
            )
        conn.commit()
        return BrandingSettingsResponse(palette=payload.palette, font_family=payload.font_family, logo_url=payload.logo_url)
    finally:
        conn.close()
