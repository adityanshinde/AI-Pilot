from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List

import numpy as np
from sklearn.cluster import DBSCAN
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.text_processing import keyword_match_count


PROBLEM_KEYWORDS = [
    "problem",
    "struggling",
    "help",
    "issue",
    "stuck",
    "can't",
    "cannot",
    "pain",
    "hard",
    "difficult",
]


@dataclass
class NLPSignals:
    is_problem: bool
    sentiment_compound: float
    keyword_matches: int


class ProblemDetector:
    def __init__(self, negative_threshold: float, min_keyword_matches: int) -> None:
        self._analyzer = SentimentIntensityAnalyzer()
        self._negative_threshold = negative_threshold
        self._min_keyword_matches = min_keyword_matches

    def analyze(self, text: str) -> NLPSignals:
        sentiment = self._analyzer.polarity_scores(text).get("compound", 0.0)
        matches = keyword_match_count(text, PROBLEM_KEYWORDS)
        is_problem = matches >= self._min_keyword_matches or sentiment <= self._negative_threshold
        return NLPSignals(
            is_problem=is_problem,
            sentiment_compound=sentiment,
            keyword_matches=matches,
        )


@dataclass
class ClusterResult:
    cluster_id: int
    item_indices: List[int]
    frequency_score: float
    trend_score: float


class ProblemClusterer:
    def __init__(self, eps: float, min_samples: int) -> None:
        self._eps = eps
        self._min_samples = min_samples

    def cluster(self, embeddings: np.ndarray, timestamps: Iterable[datetime], engagement: Iterable[float]) -> List[ClusterResult]:
        if len(embeddings) == 0:
            return []
        if len(embeddings) == 1:
            return [
                ClusterResult(
                    cluster_id=0,
                    item_indices=[0],
                    frequency_score=1.0,
                    trend_score=1.0,
                )
            ]

        model = DBSCAN(eps=self._eps, min_samples=self._min_samples, metric="cosine")
        labels = model.fit_predict(embeddings)

        grouped: dict[int, list[int]] = {}
        for idx, label in enumerate(labels):
            normalized = int(label if label >= 0 else idx + 10000)
            grouped.setdefault(normalized, []).append(idx)

        now = datetime.now(timezone.utc)
        all_counts = [len(indices) for indices in grouped.values()]
        max_count = max(all_counts) if all_counts else 1

        results: List[ClusterResult] = []
        ts_list = list(timestamps)
        engagement_list = list(engagement)

        for cid, indices in grouped.items():
            freq = len(indices) / max_count
            recency_scores = []
            engagement_scores = []
            for i in indices:
                age_hours = max((now - ts_list[i]).total_seconds() / 3600.0, 1.0)
                recency_scores.append(1.0 / math.log2(age_hours + 1.0))
                engagement_scores.append(math.log1p(max(engagement_list[i], 0.0)))

            trend = float(np.mean(recency_scores) * 0.7 + np.mean(engagement_scores) * 0.3)
            results.append(
                ClusterResult(
                    cluster_id=cid,
                    item_indices=indices,
                    frequency_score=round(freq, 4),
                    trend_score=round(trend, 4),
                )
            )

        results.sort(key=lambda r: (r.frequency_score + r.trend_score), reverse=True)
        return results
