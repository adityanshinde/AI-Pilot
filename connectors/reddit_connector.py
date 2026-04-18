from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import praw

from utils.retries import retry_api_call

logger = logging.getLogger(__name__)


class RedditConnector:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        user_agent: str,
        username: str,
        password: str,
    ) -> None:
        self._enabled = bool(client_id and client_secret and user_agent)
        self._username = username
        self._password = password
        self._client = None
        if self._enabled:
            self._client = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                username=username or None,
                password=password or None,
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @retry_api_call()
    def fetch_posts_and_comments(self, subreddits: list[str], limit: int = 50) -> list[dict[str, Any]]:
        if not self._enabled or not self._client:
            logger.warning("Reddit connector disabled due to missing credentials.")
            return []

        records: list[dict[str, Any]] = []
        for sub_name in subreddits:
            subreddit = self._client.subreddit(sub_name)
            for submission in subreddit.new(limit=limit):
                created = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                records.append(
                    {
                        "source_platform": "reddit",
                        "source_post_id": submission.id,
                        "source_type": "post",
                        "title": submission.title,
                        "body": submission.selftext or submission.title,
                        "author": str(submission.author) if submission.author else None,
                        "community": sub_name,
                        "upvotes": int(submission.score or 0),
                        "created_at_source": created,
                        "metadata_json": {
                            "url": submission.url,
                            "num_comments": submission.num_comments,
                            "permalink": f"https://reddit.com{submission.permalink}",
                        },
                    }
                )
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list()[: min(20, limit)]:
                    comment_created = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
                    records.append(
                        {
                            "source_platform": "reddit",
                            "source_post_id": comment.id,
                            "source_type": "comment",
                            "title": None,
                            "body": comment.body,
                            "author": str(comment.author) if comment.author else None,
                            "community": sub_name,
                            "upvotes": int(comment.score or 0),
                            "created_at_source": comment_created,
                            "metadata_json": {
                                "parent_post_id": submission.id,
                                "permalink": f"https://reddit.com{comment.permalink}",
                            },
                        }
                    )
        return records

    @retry_api_call()
    def publish_post(self, subreddit: str, title: str, body: str, dry_run: bool = True) -> str:
        if dry_run:
            logger.info("DRY_RUN reddit publish: %s", title)
            return "dry-run-reddit"
        if not self._enabled or not self._client:
            raise RuntimeError("Reddit credentials missing; cannot publish.")
        result = self._client.subreddit(subreddit).submit(title=title, selftext=body)
        return result.id
