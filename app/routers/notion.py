from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import setup_logger
from app.database.operations import IntegrationOperations
from app.services.notion_service import NotionService

router = APIRouter()
logger = setup_logger(__name__)


class NotionAccount(BaseModel):
    account_id: str
    app_name: str
    created_at: str
    updated_at: str


class NotionSyncRequest(BaseModel):
    user_id: str
    account_id: str
    recency_months: int = 6


class NotionSyncResponse(BaseModel):
    pages_fetched: int
    message: str


@router.get("/accounts", response_model=list[NotionAccount])
async def list_notion_accounts(user_id: str, app_name: str = None):
    try:
        accounts = IntegrationOperations.list_integrations(user_id, app_name)

    except Exception as e:
        logger.error(f"Failed to fetch integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch integrations",
        ) from e

    return accounts


@router.post("/sync", response_model=NotionSyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def sync_pages(payload: NotionSyncRequest):
    try:
        integration = IntegrationOperations.get_integration(
            user_id=payload.user_id, account_id=payload.account_id
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notion integration not found for {payload.user_id}",
            )

        logger.info(
            f"Starting Notion sync for user {payload.user_id}, account {payload.account_id}",
            "WHITE",
        )

        pages = await NotionService.fetch_pages(
            external_user_id=payload.user_id,
            account_id=payload.account_id,
            recency=payload.recency_months,
        )

        logger.info(f"Sync completed: {len(pages)} pages fetched", "WHITE")

        return NotionSyncResponse(
            pages_fetched=len(pages),
            message=f"Successfully fetched {len(pages)} pages",
        )

    except Exception as e:
        logger.error(f"Failed to sync Notion pages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync Notion pages",
        )
