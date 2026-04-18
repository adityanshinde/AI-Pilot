from __future__ import annotations

import logging

import requests

from utils.retries import retry_api_call

logger = logging.getLogger(__name__)


class BloggerConnector:
    def __init__(self, *, blog_id: str, access_token: str, api_key: str = "") -> None:
        self._blog_id = blog_id
        self._access_token = access_token
        self._api_key = api_key

    @property
    def enabled(self) -> bool:
        return bool(self._blog_id and (self._access_token or self._api_key))

    @retry_api_call()
    def publish_post(self, title: str, html_content: str, dry_run: bool = True) -> str:
        if dry_run:
            logger.info("DRY_RUN blogger publish: %s", title)
            return "dry-run-blogger"

        if not self._blog_id:
            raise RuntimeError("BLOGGER_BLOG_ID missing; cannot publish.")

        url = f"https://www.googleapis.com/blogger/v3/blogs/{self._blog_id}/posts/"
        params = {}
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        elif self._api_key:
            params["key"] = self._api_key
        else:
            raise RuntimeError("Blogger access token or API key is required.")

        payload = {
            "kind": "blogger#post",
            "title": title,
            "content": html_content,
        }
        response = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return str(response.json().get("id"))
