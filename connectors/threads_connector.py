from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from utils.retries import retry_api_call

logger = logging.getLogger(__name__)


class ThreadsConnector:
    def __init__(
        self,
        *,
        access_token: str,
        user_id: str,
        api_version: str,
        scrape_rss_url: str = "",
    ) -> None:
        self._access_token = access_token
        self._user_id = user_id
        self._api_version = api_version
        self._scrape_rss_url = scrape_rss_url

    @property
    def enabled(self) -> bool:
        return bool(self._access_token and self._user_id) or bool(self._scrape_rss_url)

    @retry_api_call()
    def fetch_posts(self, search_terms: list[str], limit: int = 25) -> list[dict[str, Any]]:
        if self._scrape_rss_url:
            return self._fetch_via_rss(limit=limit)
        if not (self._access_token and self._user_id):
            logger.warning("Threads connector disabled due to missing credentials.")
            return []

        url = f"https://graph.threads.net/{self._api_version}/{self._user_id}/threads"
        params = {
            "access_token": self._access_token,
            "fields": "id,text,timestamp,permalink,reply_audience",
            "limit": limit,
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json().get("data", [])

        records: list[dict[str, Any]] = []
        for item in payload:
            text = item.get("text", "")
            if search_terms and not any(term.lower() in text.lower() for term in search_terms):
                continue
            ts = item.get("timestamp")
            created = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now(timezone.utc)
            records.append(
                {
                    "source_platform": "threads",
                    "source_post_id": str(item.get("id")),
                    "source_type": "post",
                    "title": None,
                    "body": text,
                    "author": self._user_id,
                    "community": "threads",
                    "upvotes": 0,
                    "created_at_source": created,
                    "metadata_json": {
                        "permalink": item.get("permalink"),
                        "reply_audience": item.get("reply_audience"),
                    },
                }
            )
        return records

    @retry_api_call()
    def _fetch_via_rss(self, limit: int = 25) -> list[dict[str, Any]]:
        response = requests.get(self._scrape_rss_url, timeout=30)
        response.raise_for_status()

        records: list[dict[str, Any]] = []
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = response.json()
            items = payload.get("items", payload if isinstance(payload, list) else [])
            for item in items[:limit]:
                created = datetime.now(timezone.utc)
                if item.get("pubDate"):
                    try:
                        created = datetime.fromisoformat(item["pubDate"].replace("Z", "+00:00"))
                    except ValueError:
                        pass
                records.append(
                    {
                        "source_platform": "threads",
                        "source_post_id": str(item.get("id") or item.get("guid") or item.get("link")),
                        "source_type": "post",
                        "title": item.get("title"),
                        "body": item.get("description") or item.get("content") or "",
                        "author": item.get("author"),
                        "community": "threads",
                        "upvotes": 0,
                        "created_at_source": created,
                        "metadata_json": {"raw": item},
                    }
                )
            return records

        soup = BeautifulSoup(response.text, "xml")
        for node in soup.find_all("item")[:limit]:
            pub = node.find("pubDate")
            created = datetime.now(timezone.utc)
            if pub and pub.text:
                try:
                    created = datetime.fromisoformat(pub.text.replace("Z", "+00:00"))
                except ValueError:
                    pass
            title = node.find("title")
            desc = node.find("description")
            guid = node.find("guid")
            records.append(
                {
                    "source_platform": "threads",
                    "source_post_id": guid.text if guid else (title.text if title else str(len(records) + 1)),
                    "source_type": "post",
                    "title": title.text if title else None,
                    "body": desc.text if desc else "",
                    "author": None,
                    "community": "threads",
                    "upvotes": 0,
                    "created_at_source": created,
                    "metadata_json": {},
                }
            )
        return records

    @retry_api_call()
    def publish_post(self, text: str, dry_run: bool = True) -> str:
        if dry_run:
            logger.info("DRY_RUN threads publish: %s", text[:80])
            return "dry-run-threads"
        if not (self._access_token and self._user_id):
            raise RuntimeError("Threads credentials missing; cannot publish.")

        create_url = f"https://graph.threads.net/{self._api_version}/{self._user_id}/threads"
        create_payload = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self._access_token,
        }
        create_resp = requests.post(create_url, data=create_payload, timeout=30)
        create_resp.raise_for_status()
        creation_id = create_resp.json().get("id")

        publish_url = f"https://graph.threads.net/{self._api_version}/{self._user_id}/threads_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": self._access_token,
        }
        publish_resp = requests.post(publish_url, data=publish_payload, timeout=30)
        publish_resp.raise_for_status()
        return str(publish_resp.json().get("id", creation_id))
