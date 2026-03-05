from __future__ import annotations

import os

import httpx
from fastapi import HTTPException, status


GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google_id_token(id_token: str) -> dict:
    if not id_token.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Google ID token is required.")

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login is not configured.")

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token.")

        payload = response.json()
        if payload.get("aud") != client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token audience mismatch.")
        if payload.get("email_verified") not in ("true", True):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is not verified.")

        email = str(payload.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing email.")

        return {"email": email, "name": payload.get("name")}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to verify Google token.") from exc
