from datetime import datetime
from typing import Any

from app.config import setup_logger
from app.database.connection import supabase

logger = setup_logger(__name__)


class IntegrationOperations:
    @staticmethod
    def upsert_integration(
        user_id: str,
        app_id: str,
        app_name: str,
        account_id: str,
    ) -> dict[str, Any] | None:
        data = {
            "user_id": user_id,
            "app_id": app_id,
            "app_name": app_name,
            "account_id": account_id,
        }

        result = (
            supabase.table("integrations")
            .upsert(data, on_conflict="user_id,app_id,account_id")
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
    def update_job_status(
        job_id: str,
        status: str,
        pages_indexed: int | None = None,
        chunks_created: int | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
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
    def get_job(job_id: str) -> dict[str, Any] | None:
        result = supabase.table("indexing_jobs").select("*").eq("job_id", job_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_user_jobs(user_id: str, limit: int | None = 10) -> list[dict[str, Any]]:
        query = (
            supabase.table("indexing_jobs")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
        )
        if limit:
            query = query.limit(limit)
        result = query.execute()
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
