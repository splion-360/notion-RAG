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
    async def fetch_page_blocks(
        external_user_id: str,
        account_id: str,
        page_id: str,
        max_iterations: int = 10,
    ) -> list[dict[str, Any]]:

        all_blocks: list[dict[str, Any]] = []
        next_cursor: str | None = None
        iteration = 0

        try:
            while iteration < max_iterations:
                iteration += 1

                url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                if next_cursor:
                    url += f"?start_cursor={next_cursor}"

                response = await pipedream_client.proxy_request(
                    external_user_id=external_user_id,
                    account_id=account_id,
                    url=url,
                    method="GET",
                    headers={"Notion-Version": "2022-06-28"},
                )

                results = response.get("results", [])
                if not results:
                    break

                all_blocks.extend(results)

                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")

                if not has_more:
                    break

            if iteration >= max_iterations:
                logger.warning(
                    f"Reached max iterations ({max_iterations}) fetching blocks for page: {page_id}"
                )

            for block in all_blocks:
                if block.get("has_children"):
                    child_blocks = await NotionService.fetch_page_blocks(
                        external_user_id=external_user_id,
                        account_id=account_id,
                        page_id=block["id"],
                        max_iterations=max_iterations,
                    )
                    block["children"] = child_blocks

            return all_blocks

        except Exception as exc:
            logger.error(f"Failed to fetch blocks for page: {page_id}: {exc}")
            raise

    @staticmethod
    def extract_text_from_blocks(blocks: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:

        text_parts: list[str] = []
        media_metadata: list[dict[str, Any]] = []

        for block in blocks:
            block_text, block_media = NotionService._extract_from_single_block(block)

            if block_text:
                text_parts.append(block_text)

            if block_media:
                media_metadata.extend(block_media)

            if block.get("children"):
                child_text, child_media = NotionService.extract_text_from_blocks(block["children"])
                if child_text:
                    text_parts.append(child_text)
                if child_media:
                    media_metadata.extend(child_media)

        return ("\n".join(text_parts), media_metadata)

    @staticmethod
    def _extract_from_single_block(block: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:

        block_type = block.get("type")
        if not block_type:
            return ("", [])

        block_data = block.get(block_type, {})

        text_types = [
            "paragraph",
            "heading_1",
            "heading_2",
            "heading_3",
            "bulleted_list_item",
            "numbered_list_item",
            "quote",
            "callout",
            "code",
            "toggle",
        ]

        if block_type in text_types:
            rich_text = block_data.get("rich_text", [])
            text_content = "".join([rt.get("plain_text", "") for rt in rich_text])
            return (text_content, [])

        media_types = ["image", "video", "file", "pdf"]

        if block_type in media_types:
            caption_text = ""
            caption = block_data.get("caption", [])
            if caption:
                caption_text = "".join([c.get("plain_text", "") for c in caption])

            url = None
            if block_data.get("external"):
                url = block_data["external"].get("url")
            elif block_data.get("file"):
                url = block_data["file"].get("url")

            media_info = {
                "type": block_type,
                "url": url,
                "caption": caption_text,
            }

            placeholder = f"[{block_type.upper()}: {caption_text or 'No caption'}]"
            return (placeholder, [media_info])

        if block_type in ["bookmark", "embed"]:
            url = block_data.get("url", "")
            caption = block_data.get("caption", [])
            caption_text = "".join([c.get("plain_text", "") for c in caption])

            placeholder = f"[{block_type.upper()}: {caption_text or url}]"
            return (placeholder, [])

        return ("", [])

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
