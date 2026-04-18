from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import ContentGenerated, ProcessedProblem, PublishedLog, RawPost


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ContentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_raw_post(
        self,
        *,
        source_platform: str,
        source_post_id: str,
        source_type: str,
        title: str | None,
        body: str,
        author: str | None,
        community: str | None,
        upvotes: int,
        created_at_source: datetime,
        metadata_json: dict[str, Any],
    ) -> RawPost:
        stmt = select(RawPost).where(
            RawPost.source_platform == source_platform,
            RawPost.source_post_id == source_post_id,
            RawPost.source_type == source_type,
        )
        existing = self.session.scalar(stmt)
        if existing:
            existing.title = title
            existing.body = body
            existing.author = author
            existing.community = community
            existing.upvotes = upvotes
            existing.created_at_source = created_at_source
            existing.metadata_json = metadata_json
            self.session.flush()
            return existing

        row = RawPost(
            source_platform=source_platform,
            source_post_id=source_post_id,
            source_type=source_type,
            title=title,
            body=body,
            author=author,
            community=community,
            upvotes=upvotes,
            created_at_source=created_at_source,
            metadata_json=metadata_json,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_recent_raw_posts(self, limit: int = 300) -> list[RawPost]:
        stmt = select(RawPost).order_by(RawPost.created_at_source.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def upsert_processed_problem(
        self,
        *,
        raw_post_id: int,
        cleaned_text: str,
        problem_statement: str,
        audience: str,
        emotion: str,
        sentiment_score: float,
        cluster_id: int,
        cluster_hash: str,
        frequency_score: float,
        trend_score: float,
    ) -> ProcessedProblem:
        stmt = select(ProcessedProblem).where(ProcessedProblem.raw_post_id == raw_post_id)
        existing = self.session.scalar(stmt)
        if existing:
            existing.cleaned_text = cleaned_text
            existing.problem_statement = problem_statement
            existing.audience = audience
            existing.emotion = emotion
            existing.sentiment_score = sentiment_score
            existing.cluster_id = cluster_id
            existing.cluster_hash = cluster_hash
            existing.frequency_score = frequency_score
            existing.trend_score = trend_score
            self.session.flush()
            return existing

        row = ProcessedProblem(
            raw_post_id=raw_post_id,
            cleaned_text=cleaned_text,
            problem_statement=problem_statement,
            audience=audience,
            emotion=emotion,
            sentiment_score=sentiment_score,
            cluster_id=cluster_id,
            cluster_hash=cluster_hash,
            frequency_score=frequency_score,
            trend_score=trend_score,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def get_top_clusters(self, max_clusters: int) -> list[dict[str, Any]]:
        stmt = select(ProcessedProblem).order_by(
            (ProcessedProblem.frequency_score + ProcessedProblem.trend_score).desc(),
            ProcessedProblem.inserted_at.desc(),
        )
        problems = list(self.session.scalars(stmt).all())
        grouped: dict[str, list[ProcessedProblem]] = {}
        for p in problems:
            grouped.setdefault(p.cluster_hash, []).append(p)

        clusters: list[dict[str, Any]] = []
        for cluster_hash, rows in grouped.items():
            sample = rows[0]
            clusters.append(
                {
                    "cluster_hash": cluster_hash,
                    "problem": sample.problem_statement,
                    "audience": sample.audience,
                    "emotion": sample.emotion,
                    "frequency_score": max(r.frequency_score for r in rows),
                    "trend_score": max(r.trend_score for r in rows),
                    "examples": [r.problem_statement for r in rows[:5]],
                }
            )

        clusters.sort(key=lambda x: (x["frequency_score"] + x["trend_score"]), reverse=True)
        return clusters[:max_clusters]

    def upsert_generated_content(
        self,
        *,
        cluster_hash: str,
        content_type: str,
        topic: str,
        target_audience: str,
        angle: str,
        hook: str,
        cta: str,
        keywords: list[str],
        content_body: str,
    ) -> ContentGenerated:
        stmt = select(ContentGenerated).where(
            ContentGenerated.cluster_hash == cluster_hash,
            ContentGenerated.content_type == content_type,
        )
        content_hash = sha256_text(f"{topic}|{content_type}|{content_body}")
        existing = self.session.scalar(stmt)
        if existing:
            existing.topic = topic
            existing.target_audience = target_audience
            existing.angle = angle
            existing.hook = hook
            existing.cta = cta
            existing.keywords = keywords
            existing.content_body = content_body
            existing.content_hash = content_hash
            self.session.flush()
            return existing

        row = ContentGenerated(
            cluster_hash=cluster_hash,
            content_type=content_type,
            topic=topic,
            target_audience=target_audience,
            angle=angle,
            hook=hook,
            cta=cta,
            keywords=keywords,
            content_body=content_body,
            content_hash=content_hash,
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list_unpublished_content(self) -> list[ContentGenerated]:
        stmt = select(ContentGenerated).order_by(ContentGenerated.inserted_at.desc())
        all_content = list(self.session.scalars(stmt).all())
        out: list[ContentGenerated] = []
        for content in all_content:
            expected_platform = {
                "blog": "blogger",
                "reddit": "reddit",
                "threads": "threads",
            }.get(content.content_type)
            if not expected_platform:
                continue
            already_published = any(
                log.platform == expected_platform and log.status == "published"
                for log in content.published_logs
            )
            if not already_published:
                out.append(content)
        return out

    def add_publish_log(
        self,
        *,
        content_generated_id: int,
        platform: str,
        status: str,
        platform_post_id: str | None = None,
        error_message: str | None = None,
        dry_run: bool = True,
    ) -> PublishedLog:
        row = PublishedLog(
            content_generated_id=content_generated_id,
            platform=platform,
            status=status,
            platform_post_id=platform_post_id,
            error_message=error_message,
            dry_run=dry_run,
            published_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.session.close()
