from __future__ import annotations

from datetime import datetime

from app.core.db import get_connection
from app.schemas import DashboardResponse, GenerationHistoryItem, ResumeCard, SaveResumeResponse, UserSummary


def save_resume_snapshot(user_id: int, title: str, status: str, portfolio_json: str) -> SaveResumeResponse:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO resumes(user_id, title, status, portfolio_json) VALUES(?, ?, ?, ?)",
            (user_id, title, status, portfolio_json),
        )
        resume_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO resume_versions(resume_id, version_number, portfolio_json) VALUES(?, 1, ?)",
            (resume_id, portfolio_json),
        )
        conn.commit()
        return SaveResumeResponse(resume_id=resume_id, message="Resume saved as draft snapshot.")
    finally:
        conn.close()


def add_generation_history(user_id: int, username: str, variant_id: int, template_id: str = "auto") -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO generation_history(user_id, username, variant_id, template_id) VALUES(?, ?, ?, ?)",
            (user_id, username, variant_id, template_id),
        )
        conn.commit()
    finally:
        conn.close()


def build_dashboard(user: dict) -> DashboardResponse:
    conn = get_connection()
    try:
        resume_rows = conn.execute(
            "SELECT id, title, status, updated_at FROM resumes WHERE user_id = ? ORDER BY updated_at DESC LIMIT 30",
            (user["id"],),
        ).fetchall()
        history_rows = conn.execute(
            "SELECT id, username, variant_id, template_id, created_at FROM generation_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 30",
            (user["id"],),
        ).fetchall()

        resumes = [
            ResumeCard(
                id=int(row["id"]),
                title=row["title"],
                status=row["status"],
                updated_at=datetime.fromisoformat(str(row["updated_at"]).replace("Z", "")),
            )
            for row in resume_rows
        ]

        drafts = [item for item in resumes if item.status == "draft"]

        history = [
            GenerationHistoryItem(
                id=int(row["id"]),
                username=row["username"],
                variant_id=int(row["variant_id"]),
                template_id=row["template_id"],
                created_at=datetime.fromisoformat(str(row["created_at"]).replace("Z", "")),
            )
            for row in history_rows
        ]

        return DashboardResponse(
            user=UserSummary(
                id=user["id"],
                name=user.get("name"),
                email=user["email"],
                avatar_url=user.get("avatar_url"),
                is_admin=bool(user.get("is_admin", False)),
                is_active=bool(user.get("is_active", True)),
                created_at=datetime.fromisoformat(str(user["created_at"]).replace("Z", "")),
            ),
            my_resumes=resumes,
            saved_drafts=drafts,
            generation_history=history,
        )
    finally:
        conn.close()
