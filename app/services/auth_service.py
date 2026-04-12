from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class SupabaseAuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def sign_up(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._auth_request("/auth/v1/signup", payload)

    async def sign_in(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {"email": payload.get("email"), "password": payload.get("password")}
        return await self._auth_request("/auth/v1/token?grant_type=password", body)

    async def _auth_request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.supabase_url or not self.settings.supabase_anon_key:
            return {
                "message": "Supabase Auth is not configured yet.",
                "payload_preview": payload,
            }
        headers = {
            "apikey": self.settings.supabase_anon_key,
            "Authorization": f"Bearer {self.settings.supabase_anon_key}",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{self.settings.supabase_url}{path}", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
