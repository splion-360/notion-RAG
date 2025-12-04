from fastapi import APIRouter, HTTPException, status
from pipedream import CreateTokenResponse
from pydantic import BaseModel, Field

from app.config import setup_logger
from app.database.operations import IntegrationOperations
from app.services import PipedreamClientError, pipedream_client

router = APIRouter()
logger = setup_logger(__name__)


# Pre connection
class CreateConnectTokenRequest(BaseModel):
    external_user_id: str = Field(..., description="supabase user id")


@router.post("/connect-token", response_model=CreateTokenResponse, status_code=status.HTTP_200_OK)
async def create_connect_token(payload: CreateConnectTokenRequest) -> CreateTokenResponse:

    try:
        token = await pipedream_client.create_connect_token(payload.external_user_id)

        return token

    except PipedreamClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Pipedream connect token",
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error while creating connect token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Pipedream connect token",
        ) from e


# Post connection
class StoreIntegrationRequest(BaseModel):
    user_id: str
    app_name: str
    account_id: str


class IntegrationResponse(BaseModel):
    id: str | None
    user_id: str | None
    app_name: str | None
    account_id: str | None
    created_at: str | None
    updated_at: str | None


@router.post(
    "/integrations", response_model=IntegrationResponse | None, status_code=status.HTTP_201_CREATED
)
async def store_integration(request: StoreIntegrationRequest):

    try:
        raise
        integration = IntegrationOperations.upsert_integration(
            user_id=request.user_id,
            app_name=request.app_name,
            account_id=request.account_id,
        )

        if not integration:
            raise RuntimeError(
                f"No data returned for user {request.user_id} and account {request.account_id}"
            )

        logger.info(f"Stored integration for user {request.user_id}, app {request.app_name}")
        return integration

    except Exception as e:
        logger.error(f"Database error, attempting to roll back Pipedream connection: {e}")
        rolled_back = await pipedream_client.delete_account(
            external_user_id=request.user_id,
            account_id=request.account_id,
        )

        if rolled_back:
            logger.info(f"Rolled back Pipedream account {request.account_id}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to store integration; connection has been rolled back"
                if rolled_back
                else "Failed to store integration and roll back connection"
            ),
        ) from e


@router.get("/integrations", response_model=list[IntegrationResponse])
async def list_integrations(user_id: str):
    try:
        integrations = IntegrationOperations.list_integrations(user_id=user_id)
        return integrations

    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch integrations"
        )


@router.delete("/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(integration_id: str):
    try:
        success = IntegrationOperations.delete_integration(integration_id=integration_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found"
            )

        logger.info(f"Deleted integration {integration_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete integration"
        )
