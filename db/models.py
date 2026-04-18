from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RawPost(Base):
    __tablename__ = "raw_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_platform: Mapped[str] = mapped_column(String(40), nullable=False)
    source_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="post")
    title: Mapped[str] = mapped_column(String(700), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    community: Mapped[str] = mapped_column(String(255), nullable=True)
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at_source: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_platform", "source_post_id", "source_type", name="uq_raw_source_post_type"),
        Index("idx_raw_source_platform", "source_platform"),
        Index("idx_raw_inserted_at", "inserted_at"),
        Index("idx_raw_created_at_source", "created_at_source"),
    )


class ProcessedProblem(Base):
    __tablename__ = "processed_problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("raw_posts.id", ondelete="CASCADE"), nullable=False)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(255), nullable=False, default="general")
    emotion: Mapped[str] = mapped_column(String(80), nullable=False, default="frustrated")
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cluster_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    frequency_score: Mapped[float] = mapped_column(Float, nullable=False)
    trend_score: Mapped[float] = mapped_column(Float, nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    raw_post: Mapped[RawPost] = relationship("RawPost")

    __table_args__ = (
        UniqueConstraint("raw_post_id", name="uq_processed_raw_post"),
        Index("idx_processed_cluster_hash", "cluster_hash"),
        Index("idx_processed_inserted_at", "inserted_at"),
        Index("idx_processed_scores", "frequency_score", "trend_score"),
    )


class ContentGenerated(Base):
    __tablename__ = "content_generated"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cluster_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(255), nullable=False)
    angle: Mapped[str] = mapped_column(String(500), nullable=False)
    hook: Mapped[str] = mapped_column(String(500), nullable=False)
    cta: Mapped[str] = mapped_column(String(300), nullable=False)
    keywords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    content_body: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    published_logs: Mapped[list["PublishedLog"]] = relationship(
        "PublishedLog", back_populates="content", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("cluster_hash", "content_type", name="uq_cluster_content_type"),
        UniqueConstraint("content_hash", name="uq_content_hash"),
        Index("idx_content_cluster_hash", "cluster_hash"),
        Index("idx_content_inserted", "inserted_at"),
    )


class PublishedLog(Base):
    __tablename__ = "published_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_generated_id: Mapped[int] = mapped_column(ForeignKey("content_generated.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(40), nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    content: Mapped[ContentGenerated] = relationship("ContentGenerated", back_populates="published_logs")

    __table_args__ = (
        Index("idx_publish_platform", "platform"),
        Index("idx_publish_time", "published_at"),
        UniqueConstraint("content_generated_id", "platform", "status", name="uq_content_platform_status"),
    )
