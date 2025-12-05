from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import setup_logger
from app.database.operations import IntegrationOperations, NotionPageOperations
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

        logger.info(f"Fetched {len(pages)} page metadata", "WHITE")

        integration_id = integration["id"]
        stored_count = 0

        for page in pages:
            try:
                page_id = page.get("id")
                title = (
                    page.get("properties", {})
                    .get("title", {})
                    .get("title", [{}])[0]
                    .get("plain_text", "Untitled")
                )
                url = page.get("url")

                logger.info(f"Fetching content for page: {title}", "WHITE")

                blocks = await NotionService.fetch_page_blocks(
                    external_user_id=payload.user_id,
                    account_id=payload.account_id,
                    page_id=page_id,
                )

                content, media_metadata = NotionService.extract_text_from_blocks(blocks)

                NotionPageOperations.upsert_notion_page(
                    integration_id=integration_id,
                    notion_page_id=page_id,
                    title=title,
                    url=url,
                    content=content,
                    media_metadata=media_metadata if media_metadata else None,
                )

                stored_count += 1
                logger.info(f"Stored page: {title}", "GREEN")

            except Exception as page_error:
                logger.error(f"Failed to process page {page.get('id')}: {page_error}")
                continue

        logger.info(f"Sync completed: {stored_count}/{len(pages)} pages stored", "GREEN")

        return NotionSyncResponse(
            pages_fetched=stored_count,
            message=f"Successfully stored {stored_count} of {len(pages)} pages",
        )

    except Exception as e:
        logger.error(f"Failed to sync Notion pages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync Notion pages",
        )
