from __future__ import annotations

from typing import Any

import httpx

from .config import Settings


class SupabaseRest:
    def __init__(self, settings: Settings):
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
        self.base_url = settings.supabase_url.rstrip("/") + "/rest/v1"
        self.client = httpx.Client(
            timeout=30,
            headers={
                "apikey": settings.supabase_service_role_key,
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )

    def close(self) -> None:
        self.client.close()

    def upsert(self, table: str, rows: list[dict[str, Any]] | dict[str, Any], conflict: str) -> list[dict[str, Any]]:
        payload = rows if isinstance(rows, list) else [rows]
        if not payload:
            return []
        results: list[dict[str, Any]] = []
        batch_size = 5
        for i in range(0, len(payload), batch_size):
            batch = payload[i : i + batch_size]
            response = self.client.post(
                f"{self.base_url}/{table}",
                params={"on_conflict": conflict},
                headers={"Prefer": "resolution=merge-duplicates,return=representation"},
                json=batch,
            )
            response.raise_for_status()
            results.extend(response.json())
        return results

    def insert(self, table: str, rows: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
        payload = rows if isinstance(rows, list) else [rows]
        if not payload:
            return []
        response = self.client.post(f"{self.base_url}/{table}", json=payload)
        response.raise_for_status()
        return response.json()

    def select(self, table: str, query: dict[str, str] | None = None) -> list[dict[str, Any]]:
        response = self.client.get(f"{self.base_url}/{table}", params=query or {})
        response.raise_for_status()
        return response.json()

    def rpc(self, function_name: str, payload: dict[str, Any] | None = None) -> Any:
        response = self.client.post(f"{self.base_url}/rpc/{function_name}", json=payload or {})
        response.raise_for_status()
        return response.json()

