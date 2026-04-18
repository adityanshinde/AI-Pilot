from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    database_url: str
    log_level: str

    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    reddit_username: str
    reddit_password: str
    reddit_subreddits: List[str]
    reddit_fetch_limit: int

    threads_access_token: str
    threads_user_id: str
    threads_app_id: str
    threads_api_version: str
    threads_fetch_limit: int
    threads_search_terms: List[str]
    threads_scrape_rss_url: str

    blogger_blog_id: str
    blogger_access_token: str
    blogger_api_key: str

    dry_run: bool
    reddit_target_subreddit: str
    threads_hashtag_limit: int

    embedding_model: str
    cluster_min_samples: int
    cluster_eps: float
    negative_sentiment_threshold: float
    min_problem_keyword_matches: int

    max_clusters_per_run: int
    max_content_per_cluster: int


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@localhost:5432/autopilot_content_engine",
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "autopilot-content-engine/1.0"),
        reddit_username=os.getenv("REDDIT_USERNAME", ""),
        reddit_password=os.getenv("REDDIT_PASSWORD", ""),
        reddit_subreddits=_env_list("REDDIT_SUBREDDITS", "Entrepreneur,smallbusiness,SaaS"),
        reddit_fetch_limit=int(os.getenv("REDDIT_FETCH_LIMIT", "50")),
        threads_access_token=os.getenv("THREADS_ACCESS_TOKEN", ""),
        threads_user_id=os.getenv("THREADS_USER_ID", ""),
        threads_app_id=os.getenv("THREADS_APP_ID", ""),
        threads_api_version=os.getenv("THREADS_API_VERSION", "v1.0"),
        threads_fetch_limit=int(os.getenv("THREADS_FETCH_LIMIT", "25")),
        threads_search_terms=_env_list("THREADS_SEARCH_TERMS", "saas,help,struggling"),
        threads_scrape_rss_url=os.getenv("THREADS_SCRAPE_RSS_URL", ""),
        blogger_blog_id=os.getenv("BLOGGER_BLOG_ID", ""),
        blogger_access_token=os.getenv("BLOGGER_ACCESS_TOKEN", ""),
        blogger_api_key=os.getenv("BLOGGER_API_KEY", ""),
        dry_run=_env_bool("DRY_RUN", True),
        reddit_target_subreddit=os.getenv("REDDIT_TARGET_SUBREDDIT", "test"),
        threads_hashtag_limit=int(os.getenv("THREADS_HASHTAG_LIMIT", "6")),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        cluster_min_samples=int(os.getenv("CLUSTER_MIN_SAMPLES", "2")),
        cluster_eps=float(os.getenv("CLUSTER_EPS", "0.35")),
        negative_sentiment_threshold=float(os.getenv("NEGATIVE_SENTIMENT_THRESHOLD", "-0.15")),
        min_problem_keyword_matches=int(os.getenv("MIN_PROBLEM_KEYWORD_MATCHES", "1")),
        max_clusters_per_run=int(os.getenv("MAX_CLUSTERS_PER_RUN", "5")),
        max_content_per_cluster=int(os.getenv("MAX_CONTENT_PER_CLUSTER", "3")),
    )
