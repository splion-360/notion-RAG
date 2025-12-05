from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import setup_logger
from app.database.operations import IntegrationOperations, NotionPageOperations, PageChunkOperations
from app.services.embedding_service import embedding_service
from app.services.notion_service import NotionService
from app.utils import chunk_text

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


class NotionPageResponse(BaseModel):
    id: str
    notion_page_id: str
    title: str
    url: str
    content: str
    media_metadata: list[dict] | None
    created_at: str
    updated_at: str


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

                stored_page = NotionPageOperations.upsert_notion_page(
                    integration_id=integration_id,
                    notion_page_id=page_id,
                    title=title,
                    url=url,
                    content=content,
                    media_metadata=media_metadata if media_metadata else None,
                )

                if not stored_page:
                    logger.error(f"Failed to store page: {title}")
                    continue

                db_page_id = stored_page["id"]

                logger.info(f"Chunking and embedding page: {title}", "WHITE")

                chunks = chunk_text(content) if content else []

                if chunks:
                    logger.info(f"Generating embeddings for {len(chunks)} chunks")
                    embeddings = embedding_service.generate_embeddings_batch(chunks)

                    logger.info("Storing chunks with embeddings")
                    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        PageChunkOperations.upsert_page_chunk(
                            page_id=db_page_id,
                            chunk_index=idx,
                            content=chunk,
                            embedding=embedding,
                        )

                    logger.info(f"Stored {len(chunks)} chunks for page: {title}", "GREEN")

                stored_count += 1
                logger.info(f"Completed page: {title}", "GREEN")

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


@router.get("/pages", response_model=list[NotionPageResponse])
async def list_pages(user_id: str):
    try:
        integration = IntegrationOperations.get_integration(
            user_id=user_id, app_name="notion"
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notion integration not found for this user",
            )

        integration_id = integration["id"]
        pages = NotionPageOperations.list_notion_pages(integration_id=integration_id)

        return pages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list pages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list pages",
        )


@router.get("/pages/{page_id}", response_model=NotionPageResponse)
async def get_page(page_id: str):
    try:
        page = NotionPageOperations.get_notion_page(page_id=page_id)

        if not page:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Page not found",
            )

        return page

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get page {page_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve page",
        )
