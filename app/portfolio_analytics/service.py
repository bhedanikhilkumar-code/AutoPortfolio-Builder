from __future__ import annotations

import time
from typing import Any

from app.core.db import get_db


def track_portfolio_view(
    portfolio_id: int,
    viewer_data: dict | None = None,
) -> int:
    """Track a portfolio view."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER,
            viewer_ip TEXT,
            viewer_country TEXT,
            viewer_city TEXT,
            referrer TEXT,
            user_agent TEXT,
            viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    
    viewer_ip = viewer_data.get("ip") if viewer_data else None
    referrer = viewer_data.get("referrer") if viewer_data else None
    
    db.execute(
        "INSERT INTO portfolio_views (portfolio_id, viewer_ip, referrer) VALUES (?, ?, ?)",
        (portfolio_id, viewer_ip, referrer),
    )
    return db.total_changes


def get_portfolio_stats(portfolio_id: int) -> dict[str, Any]:
    """Get portfolio analytics."""
    db = get_db()
    
    # Total views
    views_row = db.execute(
        "SELECT COUNT(*) as count FROM portfolio_views WHERE portfolio_id = ?",
        (portfolio_id,),
    ).fetchone()
    total_views = views_row["count"] if views_row else 0
    
    # Views over time
    time_rows = db.execute(
        """
        SELECT DATE(viewed_at) as date, COUNT(*) as views
        FROM portfolio_views
        WHERE portfolio_id = ?
        GROUP BY DATE(viewed_at)
        ORDER BY date DESC
        LIMIT 30
        """,
        (portfolio_id,),
    ).fetchall()
    
    # Top referrers
    ref_rows = db.execute(
        """
        SELECT referrer, COUNT(*) as count
        FROM portfolio_views
        WHERE portfolio_id = ? AND referrer IS NOT NULL
        GROUP BY referrer
        ORDER BY count DESC
        LIMIT 5
        """,
        (portfolio_id,),
    ).fetchall()
    
    return {
        "total_views": total_views,
        "views_over_time": [
            {"date": str(r["date"]), "views": r["views"]}
            for r in time_rows
        ],
        "top_referrers": [
            {"url": r["referrer"], "count": r["count"]}
            for r in ref_rows
        ],
        "avg_daily_views": _calculate_avg_daily(total_views, time_rows),
    }


def _calculate_avg_daily(total_views: int, time_rows: list) -> float:
    """Calculate average daily views."""
    if not time_rows:
        return 0.0
    return round(total_views / len(time_rows), 2)


def get_project_click_stats(portfolio_id: int) -> dict[str, Any]:
    """Get project click analytics."""
    db = get_db()
    
    rows = db.execute(
        """
        SELECT project_name, click_count, last_clicked
        FROM project_clicks
        WHERE portfolio_id = ?
        ORDER BY click_count DESC
        """,
        (portfolio_id,),
    ).fetchall()
    
    return {
        "projects": [
            {
                "name": r["project_name"],
                "clicks": r["click_count"],
                "last_clicked": r["last_clicked"],
            }
            for r in rows
        ],
        "total_clicks": sum(r["click_count"] for r in rows),
    }


def track_project_click(
    portfolio_id: int,
    project_name: str,
) -> bool:
    """Track a project click."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS project_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id INTEGER,
            project_name TEXT,
            click_count INTEGER DEFAULT 1,
            last_clicked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    
    existing = db.execute(
        "SELECT id, click_count FROM project_clicks WHERE portfolio_id = ? AND project_name = ?",
        (portfolio_id, project_name),
    ).fetchone()
    
    if existing:
        db.execute(
            "UPDATE project_clicks SET click_count = click_count + 1, last_clicked = CURRENT_TIMESTAMP WHERE id = ?",
            (existing["id"],),
        )
    else:
        db.execute(
            "INSERT INTO project_clicks (portfolio_id, project_name, click_count) VALUES (?, ?, 1)",
            (portfolio_id, project_name),
        )
    
    return True


def get_geographic_stats(portfolio_id: int) -> dict[str, Any]:
    """Get geographic distribution of viewers."""
    db = get_db()
    
    # This would require IP geolocation - simplified version
    return {
        "countries": [],
        "cities": [],
        "note": "Configure IP geolocation service for detailed stats",
    }


def export_analytics_csv(portfolio_id: int) -> str:
    """Export analytics as CSV."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM portfolio_views WHERE portfolio_id = ? ORDER BY viewed_at DESC",
        (portfolio_id,),
    ).fetchall()
    
    if not rows:
        return "date,views\n"
    
    csv = "date,views\n"
    # Aggregate by date
    date_views = {}
    for row in rows:
        date_str = str(row["viewed_at"]).split()[0]
        date_views[date_str] = date_views.get(date_str, 0) + 1
    
    for date, views in sorted(date_views.items()):
        csv += f"{date},{views}\n"
    
    return csv