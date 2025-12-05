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
        app_id: str | None = None,
    ) -> dict[str, Any] | None:
        data = {
            "user_id": user_id,
            "app_name": app_name,
            "account_id": account_id,
        }

        if app_id:
            data["app_id"] = app_id

        result = (
            supabase.table("integrations").upsert(data, on_conflict="user_id,account_id").execute()
        )

        return result.data[0] if result.data else None

    @staticmethod
    def list_integrations(user_id: str, app_name: str = None) -> list[dict[str, Any]]:
        query = (
            supabase.table("integrations")
            .select("id, user_id, app_name, account_id, created_at, updated_at")
            .eq("user_id", user_id)
        )

        if app_name is not None:
            query = query.eq("app_name", app_name)

        result = query.execute()

        return result.data

    @staticmethod
    def get_integration(user_id: str, account_id: str) -> dict[str, Any] | None:
        result = (
            supabase.table("integrations")
            .select("*")
            .eq("user_id", user_id)
            .eq("account_id", account_id)
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


class NotionPageOperations:
    @staticmethod
    def upsert_notion_page(
        integration_id: str,
        notion_page_id: str,
        title: str | None = None,
        url: str | None = None,
        content: str | None = None,
        media_metadata: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        data = {
            "integration_id": integration_id,
            "notion_page_id": notion_page_id,
            "title": title,
            "url": url,
            "content": content,
            "media_metadata": media_metadata,
        }

        result = (
            supabase.table("notion_pages")
            .upsert(data, on_conflict="integration_id,notion_page_id")
            .execute()
        )

        return result.data[0] if result.data else None

    @staticmethod
    def get_notion_page(page_id: str) -> dict[str, Any] | None:
        result = supabase.table("notion_pages").select("*").eq("id", page_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def list_notion_pages(integration_id: str) -> list[dict[str, Any]]:
        result = (
            supabase.table("notion_pages")
            .select("*")
            .eq("integration_id", integration_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data if result.data else []
