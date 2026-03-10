from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.core.db import get_connection

SESSION_HOURS = 24


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000).hex()


def register_user(name: str, email: str, password: str) -> int:
    email_norm = email.strip().lower()
    name_clean = (name or "").strip()
    if not name_clean:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name is required.")
    if not email_norm:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required.")

    conn = get_connection()
    try:
        exists = conn.execute("SELECT id FROM users WHERE email = ?", (email_norm,)).fetchone()
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        is_admin = 1 if _is_admin_email(email_norm) else 0
        cursor = conn.execute(
            "INSERT INTO users(name, email, password_hash, password_salt, is_admin) VALUES(?, ?, ?, ?, ?)",
            (name_clean, email_norm, password_hash, salt, is_admin),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def create_session(email: str, password: str) -> tuple[str, int]:
    email_norm = email.strip().lower()
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, password_hash, password_salt, is_active FROM users WHERE email = ?", (email_norm,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        if not bool(int(row["is_active"])):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended.")

        computed = _hash_password(password, row["password_salt"])
        if computed != row["password_hash"]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        token = _create_session_row(conn, int(row["id"]))
        conn.commit()
        return token, int(row["id"])
    finally:
        conn.close()


def create_session_for_user(user_id: int) -> str:
    conn = get_connection()
    try:
        token = _create_session_row(conn, user_id)
        conn.commit()
        return token
    finally:
        conn.close()


def ensure_user_for_google(email: str, name: str | None = None, avatar_url: str | None = None) -> int:
    email_norm = email.strip().lower()
    if not email_norm:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Google account email is missing.")

    display_name = (name or "").strip() or email_norm.split("@")[0]
    avatar_clean = (avatar_url or "").strip() or None

    conn = get_connection()
    try:
        row = conn.execute("SELECT id, name, avatar_url FROM users WHERE email = ?", (email_norm,)).fetchone()
        if row:
            updates = []
            params: list[object] = []
            if display_name and display_name != (row["name"] or ""):
                updates.append("name = ?")
                params.append(display_name)
            if avatar_clean and avatar_clean != (row["avatar_url"] or ""):
                updates.append("avatar_url = ?")
                params.append(avatar_clean)
            if updates:
                params.append(int(row["id"]))
                conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
                conn.commit()
            return int(row["id"])

        salt = secrets.token_hex(16)
        random_password = secrets.token_urlsafe(24)
        password_hash = _hash_password(random_password, salt)
        is_admin = 1 if _is_admin_email(email_norm) else 0
        cursor = conn.execute(
            "INSERT INTO users(name, email, avatar_url, password_hash, password_salt, is_admin) VALUES(?, ?, ?, ?, ?, ?)",
            (display_name, email_norm, avatar_clean, password_hash, salt, is_admin),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def set_custom_avatar(user_id: int, custom_avatar_url: str | None) -> None:
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET custom_avatar_url = ? WHERE id = ?", (custom_avatar_url, int(user_id)))
        conn.commit()
    finally:
        conn.close()


def _create_session_row(conn, user_id: int) -> str:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()
    conn.execute(
        "INSERT INTO sessions(user_id, token_hash, expires_at) VALUES(?, ?, ?)",
        (int(user_id), token_hash, expires_at),
    )
    return raw_token


def _is_admin_email(email: str) -> bool:
    configured = os.getenv("ADMIN_EMAILS", "")
    if not configured.strip():
        return False
    emails = {item.strip().lower() for item in configured.split(",") if item.strip()}
    return email in emails


def revoke_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()
    finally:
        conn.close()


def resolve_user_from_token(token: str) -> dict:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.email, u.avatar_url, u.custom_avatar_url, u.is_admin, u.is_active, u.created_at, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            ORDER BY s.id DESC
            LIMIT 1
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
        if not bool(int(row["is_active"])):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended.")

        social_avatar_url = row["avatar_url"]
        custom_avatar_url = row["custom_avatar_url"]
        resolved_avatar_url = custom_avatar_url or social_avatar_url
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "email": row["email"],
            "avatar_url": resolved_avatar_url,
            "social_avatar_url": social_avatar_url,
            "custom_avatar_url": custom_avatar_url,
            "is_admin": bool(int(row["is_admin"])),
            "is_active": bool(int(row["is_active"])),
            "created_at": row["created_at"],
        }
    finally:
        conn.close()
