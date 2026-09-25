from app.providers.supabase import SupabaseGateway


class SupabaseFarmRepository:
    def __init__(self, gateway: SupabaseGateway) -> None:
        self.gateway = gateway

    async def list_for_user(self, user_id: str, user_token: str) -> list[dict]:
        return await self.gateway.get("farms", user_token, {"select": "id,name,district,area_acres,created_at", "owner_id": f"eq.{user_id}"})


class SupabaseReportRepository:
    def __init__(self, gateway: SupabaseGateway) -> None:
        self.gateway = gateway

    async def list_for_user(self, user_id: str, user_token: str) -> list[dict]:
        return await self.gateway.get("crop_reports", user_token, {"select": "id,crop_id,status,severity,created_at", "user_id": f"eq.{user_id}", "order": "created_at.desc"})
