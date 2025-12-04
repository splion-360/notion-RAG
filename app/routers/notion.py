from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.config import setup_logger
from app.database.operations import IntegrationOperations
from app.services import pipedream_client

router = APIRouter()
logger = setup_logger(__name__)


class NotionAccount(BaseModel):
    account_id: str
    app_id: str
    app_name: str
    created_at: str
    updated_at: str


@router.get("/accounts", response_model=list[NotionAccount])
async def list_notion_accounts(user_id: str = Query(..., alias="external_user_id")):
    try:
        accounts = IntegrationOperations.list_integrations(user_id)

    except Exception as e:
        logger.error(f"Failed to fetch integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch integrations",
        ) from e

    notion_accounts = [rec for rec in accounts if rec.get("app_name", "").lower() == "notion"]
    return notion_accounts


class NotionSyncRequest(BaseModel):
    account_id: str


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_notion_pages(payload: NotionSyncRequest):
    try:
        await pipedream_client.proxy_notion_request(
            external_user_id=payload.external_user_id,
            account_id=payload.account_id,
            url="https://api.notion.com/v1/search",
            body={
                "filter": {
                    "value": "page",
                    "property": "object",
                },
                "page_size": 1,
            },
        )
    except Exception as exc:
        logger.error(f"Failed to verify Notion account: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Notion via Pipedream",
        ) from exc

    return {"message": "Notion sync started"}
