from __future__ import annotations

import logging

from connectors.blogger_connector import BloggerConnector
from connectors.platform_formatter import PlatformFormatter
from connectors.reddit_connector import RedditConnector
from connectors.threads_connector import ThreadsConnector
from db.models import ContentGenerated
from db.repository import ContentRepository
from utils.config import Settings

logger = logging.getLogger(__name__)


class PublisherAgent:
    """Publishes generated content to multiple platforms with logging and retries."""

    def __init__(
        self,
        *,
        reddit_connector: RedditConnector,
        threads_connector: ThreadsConnector,
        blogger_connector: BloggerConnector,
        settings: Settings,
    ) -> None:
        self.reddit = reddit_connector
        self.threads = threads_connector
        self.blogger = blogger_connector
        self.settings = settings

    def run(self, *, repo: ContentRepository, contents: list[ContentGenerated]) -> None:
        for content in contents:
            hashtags = [kw.replace(" ", "") for kw in content.keywords][: self.settings.threads_hashtag_limit]
            if content.content_type == "blog":
                blog_html = PlatformFormatter.to_blog_html(content.content_body)
                self._publish_blogger(repo, content.id, content.topic, blog_html)
            elif content.content_type == "reddit":
                reddit_body = PlatformFormatter.to_reddit_post(content.content_body)
                self._publish_reddit(repo, content.id, content.topic, reddit_body)
            elif content.content_type == "threads":
                threads_body = PlatformFormatter.to_threads_post(content.content_body, hashtags=hashtags)
                self._publish_threads(repo, content.id, threads_body)

    def _publish_reddit(self, repo: ContentRepository, content_id: int, title: str, body: str) -> None:
        try:
            post_id = self.reddit.publish_post(
                subreddit=self.settings.reddit_target_subreddit,
                title=title[:290],
                body=body,
                dry_run=self.settings.dry_run,
            )
            repo.add_publish_log(
                content_generated_id=content_id,
                platform="reddit",
                status="published",
                platform_post_id=post_id,
                dry_run=self.settings.dry_run,
            )
        except Exception as exc:
            logger.exception("Reddit publish failed: %s", exc)
            repo.add_publish_log(
                content_generated_id=content_id,
                platform="reddit",
                status="failed",
                error_message=str(exc),
                dry_run=self.settings.dry_run,
            )

    def _publish_blogger(self, repo: ContentRepository, content_id: int, title: str, html: str) -> None:
        try:
            post_id = self.blogger.publish_post(title=title, html_content=html, dry_run=self.settings.dry_run)
            repo.add_publish_log(
                content_generated_id=content_id,
                platform="blogger",
                status="published",
                platform_post_id=post_id,
                dry_run=self.settings.dry_run,
            )
        except Exception as exc:
            logger.exception("Blogger publish failed: %s", exc)
            repo.add_publish_log(
                content_generated_id=content_id,
                platform="blogger",
                status="failed",
                error_message=str(exc),
                dry_run=self.settings.dry_run,
            )

    def _publish_threads(self, repo: ContentRepository, content_id: int, text: str) -> None:
        try:
            post_id = self.threads.publish_post(text=text, dry_run=self.settings.dry_run)
            repo.add_publish_log(
                content_generated_id=content_id,
                platform="threads",
                status="published",
                platform_post_id=post_id,
                dry_run=self.settings.dry_run,
            )
        except Exception as exc:
            logger.exception("Threads publish failed: %s", exc)
            repo.add_publish_log(
                content_generated_id=content_id,
                platform="threads",
                status="failed",
                error_message=str(exc),
                dry_run=self.settings.dry_run,
            )
