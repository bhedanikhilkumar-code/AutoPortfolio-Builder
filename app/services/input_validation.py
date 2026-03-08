from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import HTTPException, status

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
LINKEDIN_URL_RE = re.compile(r"^(?:https?://)?(?:[a-z]{2,3}\.)?(?:www\.)?linkedin\.com/in/([A-Za-z0-9-]{3,100})(?:[/?#].*)?$", re.IGNORECASE)
LINKEDIN_USERNAME_RE = re.compile(r"^[A-Za-z0-9-]{3,100}$")
GARBAGE_PATTERNS = ("asdf", "qwer", "zxcv", "sdfg", "poiuy", "lkjh", "testtest", "random")


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    message: str = ""


def is_meaningful_text(value: str, *, min_letters: int = 3, min_unique_letters: int = 3) -> bool:
    text = (value or "").strip()
    if len(text) < min_letters:
        return False
    letters = re.findall(r"[A-Za-z]", text)
    if len(letters) < min_letters:
        return False
    if len(set(ch.lower() for ch in letters)) < min_unique_letters:
        return False

    lower = text.lower()
    if any(pattern in lower for pattern in GARBAGE_PATTERNS):
        return False

    if re.fullmatch(r"[A-Za-z]{5,}", text) and not re.search(r"[aeiouAEIOU]", text):
        return False
    if re.fullmatch(r"[A-Za-z0-9]+", text) and len(text) >= 7 and not re.search(r"\s", text):
        # blocks obvious gibberish like sdfgrth / asd12345 when standalone
        if not re.search(r"[aeiouAEIOU]", text):
            return False

    vowel_count = len(re.findall(r"[aeiouAEIOU]", text))
    if len(letters) >= 6 and vowel_count == 0:
        return False
    if len(letters) >= 8 and vowel_count <= 1:
        return False

    return True


def normalize_linkedin_input(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    normalized = raw.replace("@", "", 1).strip()
    url_like = LINKEDIN_URL_RE.match(normalized)
    if url_like:
        return url_like.group(1)

    if LINKEDIN_USERNAME_RE.fullmatch(normalized):
        return normalized

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Enter a valid LinkedIn username or URL.",
    )


def validate_manual_inputs(
    *,
    name: str,
    email: str,
    github: str,
    linkedin: str | None,
    skills: list[str],
    projects: list[str],
) -> None:
    if len((name or "").strip()) < 2 or len(name.strip()) > 80 or not is_meaningful_text(name, min_letters=2, min_unique_letters=2):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid full name.")

    if not EMAIL_RE.fullmatch((email or "").strip()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid email.")

    if not github:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid GitHub username or URL.")

    if not (linkedin or "").strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid LinkedIn username or URL.")
    normalize_linkedin_input(linkedin)

    valid_skills = [item for item in skills if is_meaningful_text(item)]
    if len(valid_skills) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Please enter meaningful skills.")

    valid_projects = [item for item in projects if is_meaningful_text(item, min_letters=4, min_unique_letters=3)]
    if len(valid_projects) < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Please enter meaningful project information.")
