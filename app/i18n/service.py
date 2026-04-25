from __future__ import annotations

from typing import Any


LANGUAGES = {
    "en": {"name": "English", "native": "English", "rtl": False},
    "hi": {"name": "Hindi", "native": "हिन्दी", "rtl": False},
    "es": {"name": "Spanish", "native": "Español", "rtl": False},
    "fr": {"name": "French", "native": "Français", "rtl": False},
    "de": {"name": "German", "native": "Deutsch", "rtl": False},
    "pt": {"name": "Portuguese", "native": "Português", "rtl": False},
    "ja": {"name": "Japanese", "native": "日本語", "rtl": False},
    "ko": {"name": "Korean", "native": "한국어", "rtl": False},
    "zh": {"name": "Chinese", "native": "中文", "rtl": False},
    "ar": {"name": "Arabic", "native": "العربية", "rtl": True},
    "he": {"name": "Hebrew", "native": "עברית", "rtl": True},
    "ru": {"name": "Russian", "native": "Русский", "rtl": False},
}


def get_supported_languages() -> list[dict[str, str]]:
    """Get all supported languages."""
    return [
        {"code": code, "name": info["name"], "native": info["native"], "rtl": info["rtl"]}
        for code, info in LANGUAGES.items()
    ]


def translate_portfolio_content(
    portfolio: dict,
    target_lang: str,
) -> dict:
    """Translate portfolio content (placeholder - needs translation API)."""
    # This would integrate with Google Translate, DeepL, etc.
    # For now, returns with language marker
    
    about = portfolio.get("about", {}).get("content", {})
    name = about.get("name", "")
    
    return {
        "original_language": "en",
        "translated_language": target_lang,
        "translated_content": portfolio,
        "note": f"Translation to {LANGUAGES.get(target_lang, {}).get('name', target_lang)} requires API integration",
    }


def generate_language_switcher_html() -> str:
    """Generate language switcher HTML component."""
    return """
<select id="lang-switcher" onchange="changeLanguage(this.value)">
  <option value="en">English</option>
  <option value="hi">हिन्दी</option>
  <option value="es">Español</option>
  <option value="fr">Français</option>
  <option value="de">Deutsch</option>
  <option value="ja">日本語</option>
  <option value="ko">한국어</option>
  <option value="zh">中文</option>
  <option value="ar">العربية</option>
</select>

<script>
function changeLanguage(lang) {
  document.documentElement.lang = lang;
  // Trigger translation API call here
}
</script>
"""


def is_rtl_language(lang_code: str) -> bool:
    """Check if language is RTL."""
    return LANGUAGES.get(lang_code, {}).get("rtl", False)


def get_language_direction(lang_code: str) -> str:
    """Get text direction for language."""
    return "rtl" if is_rtl_language(lang_code) else "ltr"