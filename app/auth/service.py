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


def register_user(email: str, password: str) -> int:
    email_norm = email.strip().lower()
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
            "INSERT INTO users(email, password_hash, password_salt, is_admin) VALUES(?, ?, ?, ?)",
            (email_norm, password_hash, salt, is_admin),
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


def ensure_user_for_google(email: str) -> int:
    email_norm = email.strip().lower()
    if not email_norm:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Google account email is missing.")

    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email_norm,)).fetchone()
        if row:
            return int(row["id"])

        salt = secrets.token_hex(16)
        random_password = secrets.token_urlsafe(24)
        password_hash = _hash_password(random_password, salt)
        is_admin = 1 if _is_admin_email(email_norm) else 0
        cursor = conn.execute(
            "INSERT INTO users(email, password_hash, password_salt, is_admin) VALUES(?, ?, ?, ?)",
            (email_norm, password_hash, salt, is_admin),
        )
        conn.commit()
        return int(cursor.lastrowid)
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


def resolve_user_from_token(token: str) -> dict:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.is_admin, u.is_active, u.created_at, s.expires_at
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

        return {
            "id": int(row["id"]),
            "email": row["email"],
            "is_admin": bool(int(row["is_admin"])),
            "is_active": bool(int(row["is_active"])),
            "created_at": row["created_at"],
        }
    finally:
        conn.close()
