from __future__ import annotations

import os
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status


GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def get_google_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "").strip()


def get_google_client_secret() -> str:
    return os.getenv("GOOGLE_CLIENT_SECRET", "").strip()


def build_google_auth_url(redirect_uri: str, state: str) -> str:
    client_id = get_google_client_id()
    if not client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google login is not configured.")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "access_type": "online",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str, redirect_uri: str) -> dict:
    client_id = get_google_client_id()
    client_secret = get_google_client_secret()
    if not client_id or not client_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not fully configured.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google authorization failed.")

            token_payload = token_response.json()
            access_token = str(token_payload.get("access_token") or "").strip()
            if not access_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google access token missing.")

            user_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to load Google profile.")

            profile = user_response.json()
            email = str(profile.get("email") or "").strip().lower()
            if not email:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google profile missing email.")
            if profile.get("email_verified") not in (True, "true"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is not verified.")

            return {"email": email, "name": profile.get("name")}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach Google OAuth services.") from exc


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
