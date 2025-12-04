from typing import Any

from pipedream import AsyncPipedream, CreateTokenResponse
from pipedream.types import Account

from app.config import (
    ENVIRONMENT,
    PIPEDREAM_CLIENT_ID,
    PIPEDREAM_CLIENT_SECRET,
    PIPEDREAM_PROJECT_ID,
    setup_logger,
)

logger = setup_logger(__name__)


# Custom Exception for pipedream
class PipedreamClientError(Exception):
    def __init__(self, msg: str | None):
        message = f"Pipedream Client Error: {msg}"
        super().__init__(message)


class PipedreamService:
    def __init__(
        self,
        client_id: str = PIPEDREAM_CLIENT_ID,
        client_secret: str = PIPEDREAM_CLIENT_SECRET,
        project_id: str = PIPEDREAM_PROJECT_ID,
        environment: str = ENVIRONMENT,
    ) -> None:

        self._client = AsyncPipedream(
            client_id=client_id,
            client_secret=client_secret,
            project_id=project_id,
            project_environment=environment,
        )

    async def create_connect_token(self, external_user_id: str) -> CreateTokenResponse | None:
        if not external_user_id:
            raise PipedreamClientError("Invalid user id specified")

        try:
            response: CreateTokenResponse = await self._client.tokens.create(
                external_user_id=external_user_id,
            )
            token = response.token
            logger.info(f"Pipedream Token: {token is not None}", "GREEN")
            if not token:
                raise PipedreamClientError("Token is empty")

            return response

        except Exception as e:
            raise PipedreamClientError("Failed to create token") from e

    async def get_user_accounts(self, external_user_id: str) -> list[dict[str, Any]]:
        """
        Fetches all the integrations corresponding to the registered user with Pipedream
        """
        try:
            accounts = await self._client.accounts.list(external_user_id=external_user_id)
            logger.info(f"Fetched {len(accounts)} accounts for user {external_user_id}")
            return accounts
        except Exception as e:
            logger.error(f"Failed to get user accounts: {e}")
            raise PipedreamClientError("Failed to get user accounts") from e

    async def get_account_details(self, external_user_id: str, account_id: str) -> Account:
        try:
            account = await self._client.accounts.retrieve(account_id=account_id)
            logger.info(f"Fetched {account_id} details for {external_user_id}")
            return account
        except Exception as e:
            logger.error(f"Failed to get account details: {e}")
            raise PipedreamClientError("Failed to get account details") from e

    async def delete_account(self, external_user_id: str, account_id: str) -> bool:
        try:
            await self._client.accounts.delete(account_id=account_id)
            logger.info(f"Deleted {account_id} for {external_user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete account: {e}")
            raise PipedreamClientError("Failed to delete account") from e

    async def proxy_request(
        self,
        external_user_id: str,
        account_id: str,
        url: str,
        method: str = "POST",
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            proxy_method = getattr(self._client.proxy, method.lower())
            result = await proxy_method(
                external_user_id=external_user_id,
                account_id=account_id,
                url=url,
                body=body or {},
                headers=headers or {},
            )
            logger.info(f"Successful {method} request to {url}", "GREEN")
            return result
        except Exception as e:
            logger.error(f"Proxy request failed: {e}")
            raise PipedreamClientError("Proxy request failed") from e


pipedream_client = PipedreamService()
