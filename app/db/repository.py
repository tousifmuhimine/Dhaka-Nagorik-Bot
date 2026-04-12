from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.db.supabase_client import LocalJsonStore, SupabaseRestClient


class ComplaintRepository:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.supabase = SupabaseRestClient()
        self.local = LocalJsonStore(settings.local_storage_path)

    async def create_complaint(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.supabase.enabled:
            return await self.supabase.insert("complaints", payload)
        items = await self.local.read_items(self.local.complaints_file)
        items.append(payload)
        await self.local.write_items(self.local.complaints_file, items)
        return payload

    async def list_complaints(self) -> list[dict[str, Any]]:
        if self.supabase.enabled:
            return await self.supabase.select("complaints", {"select": "*", "order": "created_at.desc"})
        return await self.local.read_items(self.local.complaints_file)

    async def get_complaint(self, complaint_id: str) -> dict[str, Any] | None:
        items = await self.list_complaints()
        return next((item for item in items if item["id"] == complaint_id), None)

    async def update_complaint(self, complaint_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        if self.supabase.enabled:
            filters = {"id": f"eq.{complaint_id}"}
            return await self.supabase.update("complaints", filters, updates)

        items = await self.local.read_items(self.local.complaints_file)
        for item in items:
            if item["id"] == complaint_id:
                item.update(updates)
                item["updated_at"] = datetime.utcnow().isoformat()
                await self.local.write_items(self.local.complaints_file, items)
                return item
        raise KeyError(f"Complaint {complaint_id} not found")

    async def list_authorities(self) -> list[dict[str, Any]]:
        if self.supabase.enabled:
            return await self.supabase.select("authorities", {"select": "*"})
        return await self.local.read_items(self.local.authorities_file)


def get_complaint_repository() -> ComplaintRepository:
    return ComplaintRepository()
