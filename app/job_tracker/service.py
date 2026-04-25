from __future__ import annotations

from typing import Any
from datetime import datetime


def create_job_application(
    user_id: int,
    company: str,
    position: str,
    portfolio_url: str | None = None,
    status: str = "applied",
) -> str:
    """Create a job application tracker entry."""
    from app.core.db import get_connection as get_db
    
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            company TEXT,
            position TEXT,
            portfolio_url TEXT,
            status TEXT DEFAULT 'applied',
            applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
        """,
    )
    
    import secrets
    app_id = secrets.token_urlsafe(8)
    
    db.execute(
        """INSERT INTO job_applications (user_id, company, position, portfolio_url, status, id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, company, position, portfolio_url, status, app_id),
    )
    
    return app_id


def get_user_applications(user_id: int) -> list[dict[str, Any]]:
    """Get all job applications for user."""
    from app.core.db import get_connection as get_db
    
    db = get_db()
    rows = db.execute(
        """SELECT * FROM job_applications WHERE user_id = ? ORDER BY applied_date DESC""",
        (user_id,),
    ).fetchall()
    
    return [
        {
            "id": row["id"],
            "company": row["company"],
            "position": row["position"],
            "portfolio_url": row["portfolio_url"],
            "status": row["status"],
            "applied_date": row["applied_date"],
            "last_updated": row["last_updated"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def update_application_status(
    app_id: str,
    user_id: int,
    new_status: str,
    notes: str | None = None,
) -> bool:
    """Update job application status."""
    from app.core.db import get_connection as get_db
    
    db = get_db()
    
    if notes:
        db.execute(
            """UPDATE job_applications SET status = ?, notes = ?, last_updated = CURRENT_TIMESTAMP
               WHERE id = ? AND user_id = ?""",
            (new_status, notes, app_id, user_id),
        )
    else:
        db.execute(
            """UPDATE job_applications SET status = ?, last_updated = CURRENT_TIMESTAMP
               WHERE id = ? AND user_id = ?""",
            (new_status, app_id, user_id),
        )
    
    return True


def get_application_stats(user_id: int) -> dict[str, Any]:
    """Get job application statistics."""
    from app.core.db import get_connection as get_db
    
    db = get_db()
    
    rows = db.execute(
        """SELECT status, COUNT(*) as count FROM job_applications
           WHERE user_id = ? GROUP BY status""",
        (user_id,),
    ).fetchall()
    
    total = 0
    status_counts = {}
    for row in rows:
        total += row["count"]
        status_counts[row["status"]] = row["count"]
    
    return {
        "total_applications": total,
        "by_status": status_counts,
        "response_rate": round(status_counts.get("interview", 0) / total * 100, 1) if total else 0,
    }


def delete_application(app_id: str, user_id: int) -> bool:
    """Delete a job application."""
    from app.core.db import get_connection as get_db
    
    db = get_db()
    db.execute(
        "DELETE FROM job_applications WHERE id = ? AND user_id = ?",
        (app_id, user_id),
    )
    return True
