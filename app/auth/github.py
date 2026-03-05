from __future__ import annotations

import os

import httpx
from fastapi import HTTPException, status


def get_github_client_id() -> str:
    return os.getenv("GITHUB_CLIENT_ID", "").strip()


def get_github_client_secret() -> str:
    return os.getenv("GITHUB_CLIENT_SECRET", "").strip()


async def exchange_github_code(code: str) -> str:
    client_id = get_github_client_id()
    client_secret = get_github_client_secret()
    if not client_id or not client_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GitHub login is not configured.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                },
            )
            token_payload = token_res.json()
            access_token = token_payload.get("access_token")
            if not access_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub authorization failed.")
            return access_token
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach GitHub OAuth.") from exc


async def fetch_github_identity(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            user_res = await client.get("https://api.github.com/user", headers=headers)
            if user_res.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub user fetch failed.")
            user = user_res.json()

            email_res = await client.get("https://api.github.com/user/emails", headers=headers)
            email = ""
            if email_res.status_code == 200:
                emails = email_res.json()
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                fallback = next((e for e in emails if e.get("verified")), None)
                email = (primary or fallback or {}).get("email", "")

            if not email:
                email = user.get("email") or ""
            email = str(email).strip().lower()
            if not email:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub account has no public verified email.")

            return {"email": email, "name": user.get("name") or user.get("login") or email.split("@")[0]}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to fetch GitHub identity.") from exc
