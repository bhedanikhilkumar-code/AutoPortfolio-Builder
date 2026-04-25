from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from app.core.db import get_connection as get_db


# In-memory rate limit storage (use Redis in production)
RATE_LIMITS: dict[str, list[float]] = {}
API_KEYS: dict[str, dict[str, Any]] = {}


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (key_id, key)."""
    key_id = secrets.token_urlsafe(8)
    key = f"apb_{secrets.token_urlsafe(32)}"
    return key_id, key


def create_api_key(
    user_id: int,
    name: str,
    rate_limit: int = 100,
) -> tuple[str, str]:
    """Create a new API key for a user."""
    key_id, key = generate_api_key()
    key_hash = hash_api_key(key)
    
    API_KEYS[key_id] = {
        "key_hash": key_hash,
        "user_id": user_id,
        "name": name,
        "rate_limit": rate_limit,
        "created_at": time.time(),
        "is_active": True,
    }
    
    # Store in database too
    db = get_db()
    db.execute(
        """
        INSERT INTO api_keys (key_id, key_hash, user_id, name, rate_limit, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (key_id, key_hash, user_id, name, rate_limit, True),
    )
    
    return key_id, key


def validate_api_key(key: str) -> dict[str, Any] | None:
    """Validate an API key and return the key info if valid."""
    key_id = key.split("_")[1] if "_" in key else key[:8]
    key_hash = hash_api_key(key)
    
    # Check in-memory first
    if key_id in API_KEYS and API_KEYS[key_id].get("key_hash") == key_hash:
        if API_KEYS[key_id].get("is_active"):
            return API_KEYS[key_id]
    
    # Check database
    db = get_db()
    row = db.execute(
        "SELECT * FROM api_keys WHERE key_id = ? AND key_hash = ? AND is_active = true",
        (key_id, key_hash),
    ).fetchone()
    
    if row:
        return {
            "key_id": row["key_id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "rate_limit": row["rate_limit"],
        }
    
    return None


def check_rate_limit(key_id: str, rate_limit: int) -> bool:
    """Check if a request is within rate limit."""
    now = time.time()
    window = 60  # 1 minute window
    
    if key_id not in RATE_LIMITS:
        RATE_LIMITS[key_id] = []
    
    # Clean old entries
    requests = [t for t in RATE_LIMITS[key_id] if now - t < window]
    RATE_LIMITS[key_id] = requests
    
    if len(requests) >= rate_limit:
        return False
    
    requests.append(now)
    return True


def list_api_keys(user_id: int) -> list[dict[str, Any]]:
    """List all API keys for a user."""
    db = get_db()
    rows = db.execute(
        "SELECT key_id, name, rate_limit, created_at, is_active FROM api_keys WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    
    return [
        {
            "key_id": row["key_id"],
            "name": row["name"],
            "rate_limit": row["rate_limit"],
            "created_at": row["created_at"],
            "is_active": row["is_active"],
        }
        for row in rows
    ]


def revoke_api_key(key_id: str, user_id: int) -> bool:
    """Revoke an API key."""
    if key_id in API_KEYS and API_KEYS[key_id].get("user_id") == user_id:
        API_KEYS[key_id]["is_active"] = False
    
    db = get_db()
    db.execute(
        "UPDATE api_keys SET is_active = false WHERE key_id = ? AND user_id = ?",
        (key_id, user_id),
    )
    return True


def init_api_keys_db():
    """Initialize API keys table."""
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_id TEXT UNIQUE NOT NULL,
            key_hash TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            rate_limit INTEGER DEFAULT 100,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )