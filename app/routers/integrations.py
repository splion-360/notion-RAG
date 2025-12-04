from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import setup_logger
from app.database.operations import IntegrationOperations
from app.services.pipedream_service import PipedreamClientError, pipedream_client

logger = setup_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class StoreIntegrationRequest(BaseModel):
    user_id: str
    app_name: str
    account_id: str


class IntegrationResponse(BaseModel):
    id: str
    user_id: str
    app_id: str
    app_name: str
    account_id: str
    created_at: str
    updated_at: str


@router.post("", response_model=IntegrationResponse, status_code=status.HTTP_201_CREATED)
async def store_integration(request: StoreIntegrationRequest):
    try:
        account_details = await pipedream_client.get_account_details(
            external_user_id=request.user_id,
            account_id=request.account_id
        )

        app_id = account_details.get("app", {}).get("id") or account_details.get("app_id", "")

        integration = IntegrationOperations.upsert_integration(
            user_id=request.user_id,
            app_id=app_id,
            app_name=request.app_name,
            account_id=request.account_id,
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store integration"
            )

        logger.info(f"Stored integration for user {request.user_id}, app {request.app_name}")
        return integration

    except PipedreamClientError as e:
        logger.error(f"Pipedream error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch account details from Pipedream"
        )
    except Exception as e:
        logger.error(f"Unexpected error storing integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store integration"
        )


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(user_id: str):
    try:
        integrations = IntegrationOperations.list_integrations(user_id=user_id)
        return integrations
    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list integrations"
        )


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(integration_id: str):
    try:
        success = IntegrationOperations.delete_integration(integration_id=integration_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        logger.info(f"Deleted integration {integration_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete integration"
        )
