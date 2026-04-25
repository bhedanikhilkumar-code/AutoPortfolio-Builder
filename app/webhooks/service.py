from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any, Callable

import httpx
from app.core.db import get_connection as get_db


# Webhook storage
WEBHOOKS: dict[str, dict[str, Any]] = {}


def create_webhook(
    user_id: int,
    url: str,
    events: list[str],
    name: str = "default",
) -> str:
    """Create a new webhook."""
    webhook_id = secrets.token_urlsafe(8)
    secret = secrets.token_urlsafe(24)
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    
    WEBHOOKS[webhook_id] = {
        "user_id": user_id,
        "url": url,
        "events": events,
        "name": name,
        "secret_hash": secret_hash,
        "is_active": True,
        "created_at": time.time(),
    }
    
    # Store in database
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            webhook_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            events TEXT NOT NULL,
            secret_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """,
    )
    db.execute(
        """INSERT INTO webhooks (webhook_id, user_id, name, url, events, secret_hash)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (webhook_id, user_id, name, url, ",".join(events), secret_hash),
    )
    
    return webhook_id, secret


def list_webhooks(user_id: int) -> list[dict[str, Any]]:
    """List all webhooks for a user."""
    db = get_db()
    rows = db.execute(
        "SELECT webhook_id, name, url, events, is_active, created_at FROM webhooks WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    
    return [
        {
            "webhook_id": row["webhook_id"],
            "name": row["name"],
            "url": row["url"],
            "events": row["events"].split(","),
            "is_active": row["is_active"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def delete_webhook(webhook_id: str, user_id: int) -> bool:
    """Delete a webhook."""
    if webhook_id in WEBHOOKS:
        del WEBHOOKS[webhook_id]
    
    db = get_db()
    db.execute("DELETE FROM webhooks WHERE webhook_id = ? AND user_id = ?", (webhook_id, user_id))
    return True


async def trigger_webhook(
    event: str,
    payload: dict[str, Any],
    timeout: float = 5.0,
) -> dict[str, list[dict[str, str]]]:
    """Trigger webhooks for an event. Returns results by webhook."""
    results: dict[str, list[dict[str, str]]] = {"success": [], "failed": []}
    
    # Get all active webhooks for this event
    db = get_db()
    rows = db.execute(
        "SELECT webhook_id, url, secret_hash FROM webhooks WHERE is_active = true AND events LIKE ?",
        (f"%{event}%",),
    ).fetchall()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        for row in rows:
            webhook_id = row["webhook_id"]
            url = row["url"]
            
            # Prepare webhook payload
            webhook_payload = {
                "event": event,
                "timestamp": time.time(),
                "data": payload,
            }
            
            # Sign payload with secret
            import json
            body = json.dumps(webhook_payload)
            import hmac
            signature = hmac.new(
                key=row["secret_hash"].encode(),
                message=body.encode(),
                digestmod=hashlib.sha256,
            ).hexdigest()
            
            try:
                response = await client.post(
                    url,
                    json=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": f"sha256={signature}",
                        "X-Webhook-Event": event,
                    },
                )
                response.raise_for_status()
                results["success"].append({"webhook_id": webhook_id, "url": url})
            except Exception as e:
                results["failed"].append({"webhook_id": webhook_id, "url": url, "error": str(e)})
    
    return results


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret_hash: str,
) -> bool:
    """Verify webhook signature."""
    import hmac
    expected = hmac.new(
        key=secret_hash.encode(),
        message=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


# Supported webhook events
WEBHOOK_EVENTS = [
    "resume_generated",
    "resume_saved",
    "resume_shared",
    "user_registered",
    "user_login",
    "export_completed",
]
