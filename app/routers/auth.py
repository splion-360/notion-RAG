from fastapi import APIRouter, HTTPException
from pipedream import CreateTokenResponse
from pydantic import BaseModel, Field

from app.config import setup_logger
from app.services import PipedreamClientError, pipedream_client

router = APIRouter()
logger = setup_logger(__name__)


class CreateConnectTokenRequest(BaseModel):
    external_user_id: str = Field(..., description="supabase user id")


@router.post("/connect-token", response_model=CreateTokenResponse)
async def create_connect_token(payload: CreateConnectTokenRequest) -> CreateTokenResponse:

    try:
        token = await pipedream_client.create_connect_token(payload.external_user_id)

        return token

    except PipedreamClientError as e:
        raise HTTPException(
            status_code=502,
            detail="Failed to create Pipedream connect token",
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error while creating connect token: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create Pipedream connect token",
        ) from e
