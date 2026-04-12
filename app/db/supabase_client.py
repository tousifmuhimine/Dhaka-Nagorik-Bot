from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings


class LocalJsonStore:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root
        self.complaints_file = self.storage_root / "complaints.json"
        self.authorities_file = self.storage_root / "authorities.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        for path, default in (
            (self.complaints_file, []),
            (self.authorities_file, []),
        ):
            if not path.exists():
                path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")

    async def read_items(self, path: Path) -> list[dict[str, Any]]:
        def _read() -> list[dict[str, Any]]:
            return json.loads(path.read_text(encoding="utf-8"))

        return await asyncio.to_thread(_read)

    async def write_items(self, path: Path, items: list[dict[str, Any]]) -> None:
        def _write() -> None:
            path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        await asyncio.to_thread(_write)


class SupabaseRestClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.has_supabase

    async def _request(
        self,
        method: str,
        path: str,
        *,
        service_role: bool = True,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        headers = {
            "apikey": self.settings.supabase_service_role_key if service_role else self.settings.supabase_anon_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key if service_role else self.settings.supabase_anon_key}",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method=method,
                url=f"{self.settings.supabase_url}{path}",
                headers=headers,
                params=params,
                json=json_body,
            )
            response.raise_for_status()
            if response.content:
                return response.json()
            return None

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/rest/v1/{table}", params=params)
        return data or []

    async def insert(self, table: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._request(
            "POST",
            f"/rest/v1/{table}",
            json_body=payload,
            params={"select": "*"},
        )
        return (data or [{}])[0]

    async def update(self, table: str, filters: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        params = {"select": "*", **filters}
        data = await self._request("PATCH", f"/rest/v1/{table}", params=params, json_body=payload)
        return (data or [{}])[0]
