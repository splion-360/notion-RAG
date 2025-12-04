from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import setup_logger
from app.services.pipedream_service import pipedream_client

logger = setup_logger(__name__)


class NotionService:
    app_name: str = "notion"

    @staticmethod
    async def fetch_pages(
        external_user_id: str,
        account_id: str,
        recency: int = 6,
        page_size: int = 100,
        max_iterations: int = 10,
    ) -> list[dict[str, Any]]:

        if not external_user_id or not account_id:
            raise ValueError("Invalid user id or account id specified")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=recency * 30)
        collected_pages: list[dict[str, Any]] = []
        next_cursor: str | None = None
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1
                response = await NotionService._fetch_search_batch(
                    external_user_id=external_user_id,
                    account_id=account_id,
                    cursor=next_cursor,
                    page_size=page_size,
                )

                results = response.get("results", [])
                if not results:
                    break

                reached_cutoff = False
                for page in results:
                    should_include, page_reached_cutoff = NotionService._process_single_page(
                        page, cutoff_date
                    )

                    if page_reached_cutoff:
                        reached_cutoff = True
                        break

                    if should_include:
                        collected_pages.append(page)

                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")

                if reached_cutoff or not has_more:
                    break

            if iteration >= max_iterations:
                logger.warning(f"Reached max iterations ({max_iterations}), stopping pagination")

            logger.info(
                f"Fetched {len(collected_pages)} pages updated since {cutoff_date.isoformat()}",
                "WHITE",
            )
            logger.info(
                f"Pages: \n{collected_pages}",
                "GREEN",
            )

            return collected_pages

        except Exception as e:
            logger.error(f"Failed to fetch Notion pages: {e}")
            raise

    @staticmethod
    async def _fetch_search_batch(
        external_user_id: str,
        account_id: str,
        cursor: str | None,
        page_size: int,
    ) -> dict[str, Any]:

        body: dict[str, Any] = {
            "filter": {"value": "page", "property": "object"},
            "sort": {"direction": "descending", "timestamp": "last_edited_time"},
            "page_size": min(max(page_size, 1), 100),
        }

        if cursor:
            body["start_cursor"] = cursor

        response = await pipedream_client.proxy_request(
            external_user_id=external_user_id,
            account_id=account_id,
            url="https://api.notion.com/v1/search",
            method="POST",
            body=body,
            headers={"Notion-Version": "2022-06-28"},
        )

        return response

    @staticmethod
    def _process_single_page(
        page: dict[str, Any],
        cutoff_date: datetime,
    ) -> tuple[bool, bool]:

        last_edited = NotionService._parse_iso_timestamp(page.get("last_edited_time"))
        if not last_edited:
            return (False, False)

        if last_edited < cutoff_date:
            return (False, True)

        page_title = (
            page.get("properties", {})
            .get("title", {})
            .get("title", [{}])[0]
            .get("plain_text", "Untitled")
        )
        logger.info(
            f"Fetched page: {page_title} | ID: {page.get('id')} | Last edited: {last_edited.isoformat()}",
            "WHITE",
        )

        return (True, False)

    @staticmethod
    def _parse_iso_timestamp(timestamp: str | None) -> datetime | None:
        if not timestamp:
            return None
        ts = timestamp.replace("Z", "+00:00") if timestamp.endswith("Z") else timestamp
        try:
            parsed = datetime.fromisoformat(ts)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid ISO timestamp received from Notion: {timestamp}")
            return None
