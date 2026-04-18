from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class RawRecord(BaseModel):
    source_platform: str
    source_post_id: str
    source_type: str
    title: str | None = None
    body: str
    author: str | None = None
    community: str | None = None
    upvotes: int = 0
    created_at_source: datetime
    metadata_json: dict = Field(default_factory=dict)


class ProblemItem(BaseModel):
    raw_post_id: int
    cleaned_text: str
    problem_statement: str
    audience: str
    emotion: str
    sentiment_score: float
    cluster_id: int
    cluster_hash: str
    frequency_score: float
    trend_score: float


class ClusterPlan(BaseModel):
    cluster_hash: str
    blog_topic: str
    target_audience: str
    content_angle: str
    hook: str
    cta: str
    seo_keywords: List[str] = Field(default_factory=list)


class GeneratedContentBundle(BaseModel):
    cluster_hash: str
    topic: str
    target_audience: str
    angle: str
    hook: str
    cta: str
    seo_keywords: List[str] = Field(default_factory=list)
    blog_content: str
    reddit_content: str
    threads_content: str


class PublishLogInput(BaseModel):
    content_generated_id: int
    platform: str
    status: str
    external_id: str | None = None
    error_message: str | None = None
