from __future__ import annotations

from app.schemas import RewriteRequest, RewriteResponse


def rewrite_section(payload: RewriteRequest) -> RewriteResponse:
    text = payload.text.strip()
    if not text:
        return RewriteResponse(rewritten_text="")

    role_hint = f" ({payload.target_role})" if payload.target_role else ""

    if payload.mode == "concise":
        rewritten = f"{text.split('.')[0].strip()}. Impact-driven summary{role_hint}."
    elif payload.mode == "ats":
        rewritten = f"{text} Keywords: scalable systems, APIs, clean architecture{role_hint}."
    else:
        rewritten = f"Story: {text} This section highlights decisions, iterations, and outcomes{role_hint}."

    return RewriteResponse(rewritten_text=rewritten)
