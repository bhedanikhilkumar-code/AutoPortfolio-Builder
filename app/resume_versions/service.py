from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status

from app.core.db import get_connection
from app.schemas import RestoreVersionResponse, ResumeVersionItem, ResumeVersionsResponse


def list_versions(user_id: int, resume_id: int) -> ResumeVersionsResponse:
    conn = get_connection()
    try:
        owner = conn.execute("SELECT id FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user_id)).fetchone()
        if not owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

        rows = conn.execute(
            "SELECT id, resume_id, version_number, created_at FROM resume_versions WHERE resume_id = ? ORDER BY version_number DESC",
            (resume_id,),
        ).fetchall()
        return ResumeVersionsResponse(
            versions=[
                ResumeVersionItem(
                    id=int(r["id"]),
                    resume_id=int(r["resume_id"]),
                    version_number=int(r["version_number"]),
                    created_at=datetime.fromisoformat(str(r["created_at"]).replace("Z", "")),
                )
                for r in rows
            ]
        )
    finally:
        conn.close()


def restore_version(user_id: int, resume_id: int, version_number: int) -> RestoreVersionResponse:
    conn = get_connection()
    try:
        owner = conn.execute("SELECT id FROM resumes WHERE id = ? AND user_id = ?", (resume_id, user_id)).fetchone()
        if not owner:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")

        row = conn.execute(
            "SELECT portfolio_json FROM resume_versions WHERE resume_id = ? AND version_number = ?",
            (resume_id, version_number),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")

        conn.execute(
            "UPDATE resumes SET portfolio_json = ?, updated_at = datetime('now') WHERE id = ?",
            (row["portfolio_json"], resume_id),
        )
        latest = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) AS mx FROM resume_versions WHERE resume_id = ?",
            (resume_id,),
        ).fetchone()
        next_version = int(latest["mx"]) + 1
        conn.execute(
            "INSERT INTO resume_versions(resume_id, version_number, portfolio_json) VALUES(?, ?, ?)",
            (resume_id, next_version, row["portfolio_json"]),
        )
        conn.commit()
        return RestoreVersionResponse(resume_id=resume_id, restored_version=version_number, message="Version restored.")
    finally:
        conn.close()
