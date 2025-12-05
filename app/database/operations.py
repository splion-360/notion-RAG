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


class PageChunkOperations:
    @staticmethod
    def upsert_page_chunk(
        page_id: str,
        chunk_index: int,
        content: str,
        embedding: list[float],
    ) -> dict[str, Any] | None:
        data = {
            "page_id": page_id,
            "chunk_index": chunk_index,
            "content": content,
            "embedding": embedding,
        }

        result = supabase.table("page_chunks").upsert(data).execute()

        return result.data[0] if result.data else None

    @staticmethod
    def delete_page_chunks(page_id: str) -> bool:
        try:
            supabase.table("page_chunks").delete().eq("page_id", page_id).execute()
            logger.info(f"Deleted chunks for page {page_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete chunks for page {page_id}: {e}")
            return False

    @staticmethod
    def get_page_chunks(page_id: str) -> list[dict[str, Any]]:
        result = (
            supabase.table("page_chunks")
            .select("*")
            .eq("page_id", page_id)
            .order("chunk_index")
            .execute()
        )
        return result.data

    @staticmethod
    def search_similar_chunks(
        query_embedding: list[float],
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        result = supabase.rpc(
            "search_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": limit,
                "filter_user_id": user_id,
            },
        ).execute()

        return result.data


class ConversationOperations:
    @staticmethod
    def create_conversation(user_id: str, title: str | None = None) -> dict[str, Any] | None:
        data = {"user_id": user_id}
        if title:
            data["title"] = title

        result = supabase.table("conversations").insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_conversation(conversation_id: str) -> dict[str, Any] | None:
        result = supabase.table("conversations").select("*").eq("id", conversation_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def list_conversations(user_id: str) -> list[dict[str, Any]]:
        result = (
            supabase.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data if result.data else []

    @staticmethod
    def update_conversation_title(conversation_id: str, title: str) -> bool:
        try:
            supabase.table("conversations").update({"title": title}).eq(
                "id", conversation_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update conversation title: {e}")
            return False

    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        try:
            supabase.table("conversations").delete().eq("id", conversation_id).execute()
            logger.info(f"Deleted conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False


class MessageOperations:
    @staticmethod
    def create_message(
        conversation_id: str,
        role: str,
        content: str,
        chunks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }
        if chunks:
            data["chunks"] = chunks

        result = supabase.table("messages").insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_conversation_messages(conversation_id: str) -> list[dict[str, Any]]:
        result = (
            supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        return result.data if result.data else []
