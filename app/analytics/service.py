from __future__ import annotations

import json

from app.core.db import get_connection
from app.schemas import AnalyticsSummary


def record_page_view(resume_id: int) -> None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, page_views FROM portfolio_analytics WHERE resume_id = ?", (resume_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE portfolio_analytics SET page_views = page_views + 1, updated_at = datetime('now') WHERE resume_id = ?",
                (resume_id,),
            )
        else:
            conn.execute("INSERT INTO portfolio_analytics(resume_id, page_views) VALUES(?, 1)", (resume_id,))
        conn.commit()
    finally:
        conn.close()


def record_project_click(resume_id: int, project_name: str) -> None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, project_clicks_json FROM portfolio_analytics WHERE resume_id = ?", (resume_id,)).fetchone()
        if row:
            current = json.loads(row["project_clicks_json"] or "{}")
            current[project_name] = int(current.get(project_name, 0)) + 1
            conn.execute(
                "UPDATE portfolio_analytics SET project_clicks_json = ?, updated_at = datetime('now') WHERE resume_id = ?",
                (json.dumps(current), resume_id),
            )
        else:
            conn.execute(
                "INSERT INTO portfolio_analytics(resume_id, page_views, project_clicks_json) VALUES(?, 0, ?)",
                (resume_id, json.dumps({project_name: 1})),
            )
        conn.commit()
    finally:
        conn.close()


def get_analytics_for_user(user_id: int) -> AnalyticsSummary:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT a.page_views, a.project_clicks_json
            FROM portfolio_analytics a
            JOIN resumes r ON r.id = a.resume_id
            WHERE r.user_id = ?
            """,
            (user_id,),
        ).fetchall()

        total_views = 0
        total_clicks = 0
        aggregate: dict[str, int] = {}
        for row in rows:
            total_views += int(row["page_views"] or 0)
            click_map = json.loads(row["project_clicks_json"] or "{}")
            for key, value in click_map.items():
                v = int(value)
                total_clicks += v
                aggregate[key] = int(aggregate.get(key, 0)) + v

        top_projects = sorted(
            [{"name": k, "clicks": v} for k, v in aggregate.items()],
            key=lambda x: x["clicks"],
            reverse=True,
        )[:5]

        return AnalyticsSummary(
            total_views=total_views,
            total_project_clicks=total_clicks,
            top_projects=top_projects,
        )
    finally:
        conn.close()
