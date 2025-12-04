from typing import Any

from config import logger
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from app.services.pipedream_service import PipedreamClientError, pipedream_client

router = APIRouter(prefix="/auth", tags=["Authentication"])


class PipedreamConnectRequest(BaseModel):
    consumer_id: str = Field(...)
    success_url: HttpUrl
    failure_url: HttpUrl
    oauth_app_id: str | None = Field(None)
    metadata: dict[str, Any] | None = Field(None)


class PipedreamConnectResponse(BaseModel):
    connect_url: str = Field(...)
    oauth_session_id: str = Field(...)


class PipedreamProxyRequest(BaseModel):
    method: str = Field(...)
    path: str = Field(...)
    account_id: str = Field(...)
    oauth_app_id: str = Field(...)
    app_slug_name: str = Field(...)
    params: dict[str, Any] | None = Field(None)
    body: Any | None = Field(None)
    headers: dict[str, str] | None = Field(None)


class PipedreamProxyResponse(BaseModel):
    data: dict[str, Any] = Field(...)


@router.post("/connect", response_model=PipedreamConnectResponse)
async def create_pipedream_connect_session(request: PipedreamConnectRequest):
    oauth_app_id = request.oauth_app_id or pipedream_client.default_oauth_app_id
    if not oauth_app_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PIPEDREAM_OAUTH_APP_ID is not configured",
        )

    try:
        session = await pipedream_client.create_connect_session(
            consumer_id=request.consumer_id,
            oauth_app_id=oauth_app_id,
            success_url=str(request.success_url),
            failure_url=str(request.failure_url),
            metadata=request.metadata,
        )
    except PipedreamClientError as exc:
        logger.error(f"Pipedream connect failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Pipedream Connect session",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected error creating connect session: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Pipedream Connect session",
        ) from exc

    connect_url = session.get("connect_url")
    oauth_session_id = session.get("oauth_session_id") or session.get("id")

    if not connect_url or not oauth_session_id:
        logger.error(f"Pipedream response missing connect data: {session}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Pipedream returned an invalid response",
        )

    return PipedreamConnectResponse(connect_url=connect_url, oauth_session_id=oauth_session_id)


@router.post("/proxy", response_model=PipedreamProxyResponse)
async def pipedream_proxy(request: PipedreamProxyRequest):
    try:
        data = await pipedream_client.proxy_request(
            method=request.method,
            path=request.path,
            account_id=request.account_id,
            oauth_app_id=request.oauth_app_id,
            app_slug_name=request.app_slug_name,
            params=request.params,
            body=request.body,
            outbound_headers=request.headers,
        )
    except PipedreamClientError as exc:
        logger.error(f"Pipedream proxy error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Pipedream proxy call failed",
        ) from exc
    except Exception as exc:
        logger.error(f"Unexpected proxy error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pipedream proxy call failed",
        ) from exc

    return PipedreamProxyResponse(data=data)
