from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from config import logger
from app.database.connection import supabase

class UserOperations:

    @staticmethod
    def create_user(
        paragon_user_id: str,
        paragon_token: Optional[str] = None,
        paragon_token_expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        data = {
            "paragon_user_id": paragon_user_id,
            "paragon_token": paragon_token,
            "paragon_token_expires_at": paragon_token_expires_at.isoformat() if paragon_token_expires_at else None
        }
        result = supabase.table("users").insert(data).execute()
        user = result.data[0] if result.data else None
        if user:
            logger.info(f"Created user: {user['user_id']}")
        return user

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        result = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_user_by_paragon_id(paragon_user_id: str) -> Optional[Dict[str, Any]]:
        result = supabase.table("users").select("*").eq("paragon_user_id", paragon_user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def update_user_token(
        user_id: str,
        paragon_token: str,
        paragon_token_expires_at: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        data = {
            "paragon_token": paragon_token,
            "paragon_token_expires_at": paragon_token_expires_at.isoformat() if paragon_token_expires_at else None
        }
        result = supabase.table("users").update(data).eq("user_id", user_id).execute()
        user = result.data[0] if result.data else None
        if user:
            logger.info(f"Updated token for user: {user_id}")
        return user

    @staticmethod
    def update_last_indexed(user_id: str) -> Optional[Dict[str, Any]]:
        data = {"last_indexed_at": datetime.utcnow().isoformat()}
        result = supabase.table("users").update(data).eq("user_id", user_id).execute()
        user = result.data[0] if result.data else None
        if user:
            logger.info(f"Updated last_indexed_at for user: {user_id}")
        return user

class NotionPageOperations:

    @staticmethod
    def create_page(
        user_id: str,
        notion_page_id: str,
        title: Optional[str] = None,
        url: Optional[str] = None,
        created_time: Optional[datetime] = None,
        last_edited_time: Optional[datetime] = None,
        parent_type: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        data = {
            "user_id": user_id,
            "notion_page_id": notion_page_id,
            "title": title,
            "url": url,
            "created_time": created_time.isoformat() if created_time else None,
            "last_edited_time": last_edited_time.isoformat() if last_edited_time else None,
            "parent_type": parent_type,
            "parent_id": parent_id,
            "metadata": metadata
        }
        result = supabase.table("notion_pages").insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_page_by_notion_id(notion_page_id: str) -> Optional[Dict[str, Any]]:
        result = supabase.table("notion_pages").select("*").eq("notion_page_id", notion_page_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_user_pages(user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        query = supabase.table("notion_pages").select("*").eq("user_id", user_id).order("last_edited_time", desc=True)
        if limit:
            query = query.limit(limit)
        result = query.execute()
        return result.data if result.data else []

    @staticmethod
    def upsert_page(
        user_id: str,
        notion_page_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        existing = NotionPageOperations.get_page_by_notion_id(notion_page_id)

        if existing:

            update_data = {k: v for k, v in kwargs.items() if v is not None}

            for key in ["created_time", "last_edited_time"]:
                if key in update_data and isinstance(update_data[key], datetime):
                    update_data[key] = update_data[key].isoformat()
            update_data["indexed_at"] = datetime.utcnow().isoformat()

            result = supabase.table("notion_pages").update(update_data).eq("notion_page_id", notion_page_id).execute()
            return result.data[0] if result.data else None
        else:

            return NotionPageOperations.create_page(user_id, notion_page_id, **kwargs)

class PageChunkOperations:

    @staticmethod
    def create_chunk(
        page_id: str,
        user_id: str,
        content: str,
        embedding: Optional[List[float]] = None,
        chunk_index: int = 0,
        token_count: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        data = {
            "page_id": page_id,
            "user_id": user_id,
            "content": content,
            "embedding": embedding,
            "chunk_index": chunk_index,
            "token_count": token_count,
            "metadata": metadata
        }
        result = supabase.table("page_chunks").insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_page_chunks(page_id: str) -> List[Dict[str, Any]]:
        result = supabase.table("page_chunks").select("*").eq("page_id", page_id).order("chunk_index").execute()
        return result.data if result.data else []

    @staticmethod
    def delete_page_chunks(page_id: str) -> int:
        result = supabase.table("page_chunks").delete().eq("page_id", page_id).execute()
        return len(result.data) if result.data else 0

    @staticmethod
    def search_similar_chunks(
        user_id: str,
        query_embedding: List[float],
        limit: int = 10
    ) -> List[Dict[str, Any]]:

        result = supabase.rpc(
            "search_chunks",
            {
                "query_embedding": query_embedding,
                "query_user_id": user_id,
                "match_count": limit
            }
        ).execute()

        return result.data if result.data else []

class IndexingJobOperations:

    @staticmethod
    def create_job(user_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        data = {
            "user_id": user_id,
            "metadata": metadata
        }
        result = supabase.table("indexing_jobs").insert(data).execute()
        job = result.data[0] if result.data else None
        if job:
            logger.info(f"Created indexing job: {job['job_id']}")
        return job

    @staticmethod
    def update_job_status(
        job_id: str,
        status: str,
        pages_indexed: Optional[int] = None,
        chunks_created: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        data = {"status": status}

        if status == "running":
            data["started_at"] = datetime.utcnow().isoformat()
        elif status in ["completed", "failed"]:
            data["completed_at"] = datetime.utcnow().isoformat()

        if pages_indexed is not None:
            data["pages_indexed"] = pages_indexed
        if chunks_created is not None:
            data["chunks_created"] = chunks_created
        if error_message:
            data["error_message"] = error_message

        result = supabase.table("indexing_jobs").update(data).eq("job_id", job_id).execute()
        job = result.data[0] if result.data else None
        if job:
            logger.info(f"Updated job {job_id} status to: {status}")
        return job

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        result = supabase.table("indexing_jobs").select("*").eq("job_id", job_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_user_jobs(user_id: str, limit: Optional[int] = 10) -> List[Dict[str, Any]]:
        query = supabase.table("indexing_jobs").select("*").eq("user_id", user_id).order("created_at", desc=True)
        if limit:
            query = query.limit(limit)
        result = query.execute()
        return result.data if result.data else []
