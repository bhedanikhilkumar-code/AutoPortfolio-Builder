from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from app.core.db import get_connection as get_db


NOTIFICATIONS: dict[str, dict[str, Any]] = {}


def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    data: dict | None = None,
) -> str:
    """Create a notification for user."""
    notification_id = secrets.token_urlsafe(8)
    
    NOTIFICATIONS[notification_id] = {
        "user_id": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "is_read": False,
        "created_at": time.time(),
    }
    
    # Store in database
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_id TEXT UNIQUE,
            user_id INTEGER,
            type TEXT,
            title TEXT,
            message TEXT,
            data TEXT,
            is_read BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    db.execute(
        """INSERT INTO notifications (notification_id, user_id, type, title, message, data)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (notification_id, user_id, notification_type, title, message, str(data or {})),
    )
    
    return notification_id


def get_user_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get notifications for user."""
    db = get_db()
    
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params = [user_id]
    
    if unread_only:
        query += " AND is_read = false"
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    rows = db.execute(query, params).fetchall()
    
    return [
        {
            "notification_id": row["notification_id"],
            "type": row["type"],
            "title": row["title"],
            "message": row["message"],
            "is_read": row["is_read"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def mark_as_read(notification_id: str, user_id: int) -> bool:
    """Mark notification as read."""
    if notification_id in NOTIFICATIONS:
        NOTIFICATIONS[notification_id]["is_read"] = True
    
    db = get_db()
    db.execute(
        "UPDATE notifications SET is_read = true WHERE notification_id = ? AND user_id = ?",
        (notification_id, user_id),
    )
    return True


def mark_all_read(user_id: int) -> int:
    """Mark all notifications as read for user."""
    db = get_db()
    db.execute(
        "UPDATE notifications SET is_read = true WHERE user_id = ? AND is_read = false",
        (user_id,),
    )
    
    for notif in NOTIFICATIONS.values():
        if notif.get("user_id") == user_id:
            notif["is_read"] = True
    
    return db.total_changes


def delete_notification(notification_id: str, user_id: int) -> bool:
    """Delete a notification."""
    if notification_id in NOTIFICATIONS:
        del NOTIFICATIONS[notification_id]
    
    db = get_db()
    db.execute(
        "DELETE FROM notifications WHERE notification_id = ? AND user_id = ?",
        (notification_id, user_id),
    )
    return True


def get_unread_count(user_id: int) -> int:
    """Get count of unread notifications."""
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = false",
        (user_id,),
    ).fetchone()
    
    return row["count"] if row else 0


# Notification templates
def notify_resume_generated(user_id: int, resume_title: str) -> str:
    """Notify when resume is generated."""
    return create_notification(
        user_id=user_id,
        notification_type="resume_generated",
        title="Resume Generated",
        message=f"Your resume '{resume_title}' has been generated successfully.",
        data={"resume_title": resume_title},
    )


def notify_resume_saved(user_id: int, resume_title: str) -> str:
    """Notify when resume is saved."""
    return create_notification(
        user_id=user_id,
        notification_type="resume_saved",
        title="Resume Saved",
        message=f"Your resume '{resume_title}' has been saved.",
        data={"resume_title": resume_title},
    )


def notify_export_completed(user_id: int, export_format: str) -> str:
    """Notify when export is completed."""
    return create_notification(
        user_id=user_id,
        notification_type="export_completed",
        title="Export Complete",
        message=f"Your portfolio has been exported as {export_format}.",
        data={"format": export_format},
    )


def notify_share_link_created(user_id: int, share_url: str) -> str:
    """Notify when share link is created."""
    return create_notification(
        user_id=user_id,
        notification_type="share_created",
        title="Share Link Created",
        message=f"A shareable link has been created for your portfolio.",
        data={"share_url": share_url},
    )


def notify_low_seo_score(user_id: int, score: int) -> str:
    """Notify about low SEO score."""
    return create_notification(
        user_id=user_id,
        notification_type="seo_alert",
        title="Improve Your SEO Score",
        message=f"Your portfolio SEO score is {score}. Consider adding more information.",
        data={"score": score},
    )
