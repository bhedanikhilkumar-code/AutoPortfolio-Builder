from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from app.core.db import get_connection
from app.schemas import (
    AdminActionResponse,
    AdminActivityItem,
    AdminActivityResponse,
    AdminResumeItem,
    AdminResumesResponse,
    AdminStatsResponse,
    AdminUserItem,
    AdminUsersResponse,
)


def get_admin_stats() -> AdminStatsResponse:
    conn = get_connection()
    try:
        total_users = int(conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"])
        total_admins = int(conn.execute("SELECT COUNT(*) AS count FROM users WHERE is_admin = 1").fetchone()["count"])
        total_resumes = int(conn.execute("SELECT COUNT(*) AS count FROM resumes").fetchone()["count"])
        total_drafts = int(conn.execute("SELECT COUNT(*) AS count FROM resumes WHERE status = 'draft'").fetchone()["count"])
        total_published = int(conn.execute("SELECT COUNT(*) AS count FROM resumes WHERE status = 'published'").fetchone()["count"])
        total_generations = int(conn.execute("SELECT COUNT(*) AS count FROM generation_history").fetchone()["count"])
        return AdminStatsResponse(
            total_users=total_users,
            total_admins=total_admins,
            total_resumes=total_resumes,
            total_drafts=total_drafts,
            total_published=total_published,
            total_generations=total_generations,
        )
    finally:
        conn.close()


def get_admin_users_overview(limit: int = 100) -> AdminUsersResponse:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                u.id,
                u.email,
                u.is_admin,
                u.is_active,
                u.created_at,
                COALESCE(r.resume_count, 0) AS resume_count,
                COALESCE(g.generation_count, 0) AS generation_count
            FROM users u
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS resume_count
                FROM resumes
                GROUP BY user_id
            ) r ON r.user_id = u.id
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS generation_count
                FROM generation_history
                GROUP BY user_id
            ) g ON g.user_id = u.id
            ORDER BY u.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        users = [
            AdminUserItem(
                id=int(row["id"]),
                email=row["email"],
                is_admin=bool(int(row["is_admin"])),
                is_active=bool(int(row["is_active"])),
                resume_count=int(row["resume_count"]),
                generation_count=int(row["generation_count"]),
                created_at=datetime.fromisoformat(str(row["created_at"]).replace("Z", "")),
            )
            for row in rows
        ]
        return AdminUsersResponse(users=users)
    finally:
        conn.close()


def get_admin_resumes_overview(limit: int = 200) -> AdminResumesResponse:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT r.id, r.user_id, u.email AS owner_email, r.title, r.status, r.updated_at
            FROM resumes r
            JOIN users u ON u.id = r.user_id
            ORDER BY r.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        resumes = [
            AdminResumeItem(
                id=int(row["id"]),
                user_id=int(row["user_id"]),
                owner_email=row["owner_email"],
                title=row["title"],
                status=row["status"],
                updated_at=datetime.fromisoformat(str(row["updated_at"]).replace("Z", "")),
            )
            for row in rows
        ]
        return AdminResumesResponse(resumes=resumes)
    finally:
        conn.close()


def suspend_user(admin_user_id: int, user_id: int) -> AdminActionResponse:
    return _set_user_active_state(admin_user_id, user_id, False)


def activate_user(admin_user_id: int, user_id: int) -> AdminActionResponse:
    return _set_user_active_state(admin_user_id, user_id, True)


def force_publish_resume(admin_user_id: int, resume_id: int) -> AdminActionResponse:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
        conn.execute("UPDATE resumes SET status = 'published', updated_at = datetime('now') WHERE id = ?", (resume_id,))
        _log_admin_action(conn, admin_user_id, "force_publish", "resume", resume_id, "Status set to published")
        conn.commit()
        return AdminActionResponse(message="Resume force-published.")
    finally:
        conn.close()


def delete_resume_admin(admin_user_id: int, resume_id: int) -> AdminActionResponse:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM resumes WHERE id = ?", (resume_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
        conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
        _log_admin_action(conn, admin_user_id, "delete", "resume", resume_id, "Resume deleted by admin")
        conn.commit()
        return AdminActionResponse(message="Resume deleted.")
    finally:
        conn.close()


def get_admin_activity(limit: int = 100) -> AdminActivityResponse:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, admin_user_id, action, target_type, target_id, details, created_at
            FROM admin_activity_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        logs = [
            AdminActivityItem(
                id=int(row["id"]),
                admin_user_id=int(row["admin_user_id"]),
                action=row["action"],
                target_type=row["target_type"],
                target_id=int(row["target_id"]),
                details=row["details"],
                created_at=datetime.fromisoformat(str(row["created_at"]).replace("Z", "")),
            )
            for row in rows
        ]
        return AdminActivityResponse(logs=logs)
    finally:
        conn.close()


def _set_user_active_state(admin_user_id: int, user_id: int, is_active: bool) -> AdminActionResponse:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
        action = "activate" if is_active else "suspend"
        _log_admin_action(conn, admin_user_id, action, "user", user_id, f"User marked {'active' if is_active else 'suspended'}")
        conn.commit()
        return AdminActionResponse(message=f"User {'activated' if is_active else 'suspended' }.")
    finally:
        conn.close()


def _log_admin_action(conn, admin_user_id: int, action: str, target_type: str, target_id: int, details: str | None = None) -> None:
    conn.execute(
        "INSERT INTO admin_activity_logs(admin_user_id, action, target_type, target_id, details) VALUES(?, ?, ?, ?, ?)",
        (admin_user_id, action, target_type, target_id, details),
    )
