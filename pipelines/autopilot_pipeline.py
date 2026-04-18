from __future__ import annotations

import logging
import os

from agents import (
    ContentGeneratorAgent,
    ContentStrategistAgent,
    PainPointAnalyzerAgent,
    PublisherAgent,
    TrendMinerAgent,
)
from connectors import BloggerConnector, RedditConnector, ThreadsConnector
from db import init_db
from db.repository import ContentRepository
from db.session import get_session
from utils.config import Settings, get_settings
from utils.nlp import ProblemClusterer, ProblemDetector

logger = logging.getLogger(__name__)


class AutopilotContentPipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.settings.openai_api_key)

        self.reddit_connector = RedditConnector(
            client_id=self.settings.reddit_client_id,
            client_secret=self.settings.reddit_client_secret,
            user_agent=self.settings.reddit_user_agent,
            username=self.settings.reddit_username,
            password=self.settings.reddit_password,
        )
        self.threads_connector = ThreadsConnector(
            access_token=self.settings.threads_access_token,
            user_id=self.settings.threads_user_id,
            api_version=self.settings.threads_api_version,
            scrape_rss_url=self.settings.threads_scrape_rss_url,
        )
        self.blogger_connector = BloggerConnector(
            blog_id=self.settings.blogger_blog_id,
            access_token=self.settings.blogger_access_token,
            api_key=self.settings.blogger_api_key,
        )

        self.trend_agent = TrendMinerAgent(
            reddit_connector=self.reddit_connector,
            threads_connector=self.threads_connector,
        )
        self.analyzer_agent = PainPointAnalyzerAgent(
            detector=ProblemDetector(
                negative_threshold=self.settings.negative_sentiment_threshold,
                min_keyword_matches=self.settings.min_problem_keyword_matches,
            ),
            clusterer=ProblemClusterer(
                eps=self.settings.cluster_eps,
                min_samples=self.settings.cluster_min_samples,
            ),
            embedding_model=self.settings.embedding_model,
        )
        self.strategist_agent = ContentStrategistAgent(model=self.settings.openai_model)
        self.generator_agent = ContentGeneratorAgent(model=self.settings.openai_model)
        self.publisher_agent = PublisherAgent(
            reddit_connector=self.reddit_connector,
            threads_connector=self.threads_connector,
            blogger_connector=self.blogger_connector,
            settings=self.settings,
        )

    def run_once(self, ensure_db: bool = True) -> None:
        if ensure_db:
            init_db()

        session = get_session()
        repo = ContentRepository(session)
        try:
            self.trend_agent.run(
                repo=repo,
                subreddits=self.settings.reddit_subreddits,
                reddit_limit=self.settings.reddit_fetch_limit,
                threads_terms=self.settings.threads_search_terms,
                threads_limit=self.settings.threads_fetch_limit,
            )
            repo.commit()

            self.analyzer_agent.run(repo=repo)
            repo.commit()

            clusters = repo.get_top_clusters(max_clusters=self.settings.max_clusters_per_run)
            if not clusters:
                logger.info("No clusters available; ending pipeline run.")
                return

            plans = self.strategist_agent.run(clusters=clusters, max_clusters=self.settings.max_clusters_per_run)
            bundles = self.generator_agent.run(plans=plans[: self.settings.max_content_per_cluster])

            for bundle in bundles:
                repo.upsert_generated_content(
                    cluster_hash=bundle.cluster_hash,
                    content_type="blog",
                    topic=bundle.topic,
                    target_audience=bundle.target_audience,
                    angle=bundle.angle,
                    hook=bundle.hook,
                    cta=bundle.cta,
                    keywords=bundle.seo_keywords,
                    content_body=bundle.blog_content,
                )
                repo.upsert_generated_content(
                    cluster_hash=bundle.cluster_hash,
                    content_type="reddit",
                    topic=bundle.topic,
                    target_audience=bundle.target_audience,
                    angle=bundle.angle,
                    hook=bundle.hook,
                    cta=bundle.cta,
                    keywords=bundle.seo_keywords,
                    content_body=bundle.reddit_content,
                )
                repo.upsert_generated_content(
                    cluster_hash=bundle.cluster_hash,
                    content_type="threads",
                    topic=bundle.topic,
                    target_audience=bundle.target_audience,
                    angle=bundle.angle,
                    hook=bundle.hook,
                    cta=bundle.cta,
                    keywords=bundle.seo_keywords,
                    content_body=bundle.threads_content,
                )
            repo.commit()

            unpublished = repo.list_unpublished_content()
            self.publisher_agent.run(repo=repo, contents=unpublished)
            repo.commit()

            logger.info(
                "Pipeline completed. clusters=%d plans=%d bundles=%d published_candidates=%d",
                len(clusters),
                len(plans),
                len(bundles),
                len(unpublished),
            )
        except Exception:
            repo.rollback()
            logger.exception("Pipeline failed and transaction was rolled back.")
            raise
        finally:
            repo.close()
