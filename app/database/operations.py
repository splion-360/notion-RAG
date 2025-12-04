from typing import Any

from app.config import setup_logger
from app.database.connection import supabase

logger = setup_logger(__name__)


class IntegrationOperations:
    @staticmethod
    def upsert_integration(
        user_id: str,
        app_name: str,
        account_id: str,
    ) -> dict[str, Any] | None:
        data = {
            "user_id": user_id,
            "app_name": app_name,
            "account_id": account_id,
        }

        result = (
            supabase.table("integrations")
            .upsert(data, on_conflict="user_id,account_id")
            .execute()
        )

        return result.data[0] if result.data else None

    @staticmethod
    def list_integrations(user_id: str) -> list[dict[str, Any]]:
        result = (
            supabase.table("integrations")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return result.data if result.data else []

    @staticmethod
    def get_integration(user_id: str, app_name: str) -> dict[str, Any] | None:
        result = (
            supabase.table("integrations")
            .select("*")
            .eq("user_id", user_id)
            .eq("app_name", app_name)
            .execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    def delete_integration(integration_id: str) -> bool:
        try:
            supabase.table("integrations").delete().eq("id", integration_id).execute()
            logger.info(f"Deleted integration {integration_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete integration {integration_id}: {e}")
            return False
