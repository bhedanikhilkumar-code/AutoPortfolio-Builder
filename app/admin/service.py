from __future__ import annotations

from datetime import datetime

from app.core.db import get_connection
from app.schemas import AdminResumeItem, AdminResumesResponse, AdminStatsResponse, AdminUserItem, AdminUsersResponse


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
