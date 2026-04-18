from __future__ import annotations

import logging
from collections import Counter
from datetime import timezone

from agents.schemas import ProblemItem
from db.repository import ContentRepository, sha256_text
from utils.embeddings import embed_texts
from utils.nlp import ProblemClusterer, ProblemDetector
from utils.text_processing import clean_text

logger = logging.getLogger(__name__)


class PainPointAnalyzerAgent:
    """Detects, embeds, clusters, and persists user pain points."""

    def __init__(
        self,
        *,
        detector: ProblemDetector,
        clusterer: ProblemClusterer,
        embedding_model: str,
    ) -> None:
        self.detector = detector
        self.clusterer = clusterer
        self.embedding_model = embedding_model

    def run(self, *, repo: ContentRepository, scan_limit: int = 300) -> list[ProblemItem]:
        raw_posts = repo.list_recent_raw_posts(limit=scan_limit)
        candidates = []
        for post in raw_posts:
            text = clean_text(f"{post.title or ''} {post.body or ''}")
            if not text:
                continue
            signals = self.detector.analyze(text)
            if not signals.is_problem:
                continue
            candidates.append((post, text, signals))

        if not candidates:
            logger.info("PainPointAnalyzerAgent found no candidates.")
            return []

        texts = [item[1] for item in candidates]
        timestamps = [item[0].created_at_source.astimezone(timezone.utc) for item in candidates]
        engagement = [float(item[0].upvotes) for item in candidates]
        embeddings = embed_texts(texts, self.embedding_model)
        clusters = self.clusterer.cluster(embeddings=embeddings, timestamps=timestamps, engagement=engagement)

        cluster_map: dict[int, tuple[float, float, str]] = {}
        for c in clusters:
            phrases = [texts[i] for i in c.item_indices]
            cluster_hash = sha256_text("|".join(sorted(phrases[:10])))
            for i in c.item_indices:
                cluster_map[i] = (c.frequency_score, c.trend_score, cluster_hash)

        items: list[ProblemItem] = []
        for idx, (post, text, signals) in enumerate(candidates):
            frequency, trend, cluster_hash = cluster_map.get(idx, (1.0, 1.0, sha256_text(text)))
            audience = post.community or "general online users"
            emotion = self._emotion_from_signal(signals.sentiment_compound)
            statement = self._normalize_statement(text)
            cluster_id = self._cluster_id_from_hash(cluster_hash)

            repo.upsert_processed_problem(
                raw_post_id=post.id,
                cleaned_text=text,
                problem_statement=statement,
                audience=audience,
                emotion=emotion,
                sentiment_score=signals.sentiment_compound,
                cluster_id=cluster_id,
                cluster_hash=cluster_hash,
                frequency_score=frequency,
                trend_score=trend,
            )
            items.append(
                ProblemItem(
                    raw_post_id=post.id,
                    cleaned_text=text,
                    problem_statement=statement,
                    audience=audience,
                    emotion=emotion,
                    sentiment_score=signals.sentiment_compound,
                    cluster_id=cluster_id,
                    cluster_hash=cluster_hash,
                    frequency_score=frequency,
                    trend_score=trend,
                )
            )

        logger.info("PainPointAnalyzerAgent processed %d pain points", len(items))
        return items

    @staticmethod
    def _emotion_from_signal(compound: float) -> str:
        if compound <= -0.6:
            return "desperate"
        if compound <= -0.35:
            return "frustrated"
        if compound <= -0.1:
            return "concerned"
        return "neutral"

    @staticmethod
    def _normalize_statement(text: str) -> str:
        parts = [p.strip() for p in text.split(".") if p.strip()]
        return parts[0][:500] if parts else text[:500]

    @staticmethod
    def _cluster_id_from_hash(cluster_hash: str) -> int:
        return int(cluster_hash[:8], 16)
