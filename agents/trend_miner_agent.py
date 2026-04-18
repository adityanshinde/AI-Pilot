from __future__ import annotations

import logging
from typing import Iterable

from agents.schemas import RawRecord
from connectors.reddit_connector import RedditConnector
from connectors.threads_connector import ThreadsConnector
from db.repository import ContentRepository

logger = logging.getLogger(__name__)


class TrendMinerAgent:
    """Fetches social platform data and persists normalized raw records."""

    def __init__(
        self,
        *,
        reddit_connector: RedditConnector,
        threads_connector: ThreadsConnector,
    ) -> None:
        self.reddit = reddit_connector
        self.threads = threads_connector

    def run(
        self,
        *,
        repo: ContentRepository,
        subreddits: list[str],
        reddit_limit: int,
        threads_terms: list[str],
        threads_limit: int,
    ) -> list[RawRecord]:
        records: list[RawRecord] = []

        if self.reddit.enabled:
            logger.info("Fetching Reddit posts/comments from %s", ",".join(subreddits))
            reddit_records = self.reddit.fetch_posts_and_comments(subreddits=subreddits, limit=reddit_limit)
            records.extend(RawRecord.model_validate(r) for r in reddit_records)

        if self.threads.enabled:
            logger.info("Fetching Threads posts")
            thread_records = self.threads.fetch_posts(search_terms=threads_terms, limit=threads_limit)
            records.extend(RawRecord.model_validate(r) for r in thread_records)

        persisted = self._persist(repo, records)
        logger.info("TrendMinerAgent persisted %d raw records", len(persisted))
        return persisted

    def _persist(self, repo: ContentRepository, records: Iterable[RawRecord]) -> list[RawRecord]:
        saved: list[RawRecord] = []
        for r in records:
            row = repo.upsert_raw_post(
                source_platform=r.source_platform,
                source_post_id=r.source_post_id,
                source_type=r.source_type,
                title=r.title,
                body=r.body,
                author=r.author,
                community=r.community,
                upvotes=r.upvotes,
                created_at_source=r.created_at_source,
                metadata_json=r.metadata_json,
            )
            saved.append(
                RawRecord(
                    source_platform=row.source_platform,
                    source_post_id=row.source_post_id,
                    source_type=row.source_type,
                    title=row.title,
                    body=row.body,
                    author=row.author,
                    community=row.community,
                    upvotes=row.upvotes,
                    created_at_source=row.created_at_source,
                    metadata_json=row.metadata_json,
                )
            )
        return saved
