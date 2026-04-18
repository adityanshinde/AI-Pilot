from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from agents.schemas import ClusterPlan
from utils.llm import extract_json, run_crewai_task

logger = logging.getLogger(__name__)


class ContentStrategistAgent:
    """Builds prioritized content plans from clustered pain points."""

    def __init__(self, *, model: str, prompt_path: str = "prompts/content_strategist_prompt.txt") -> None:
        self.model = model
        self.prompt_text = Path(prompt_path).read_text(encoding="utf-8")

    def run(self, clusters: list[dict[str, Any]], max_clusters: int) -> list[ClusterPlan]:
        input_clusters = clusters[:max_clusters]
        if not input_clusters:
            return []

        try:
            description = (
                f"{self.prompt_text}\n\n"
                f"Input clusters JSON:\n{json.dumps(input_clusters, ensure_ascii=False, indent=2)}\n\n"
                "Return ONLY a JSON array with unique topic ideas."
            )
            result = run_crewai_task(
                role="Content Strategist",
                goal="Convert user pain-point clusters into high-converting content plans.",
                backstory="Senior growth strategist focused on problem-aware educational content.",
                description=description,
                expected_output="JSON array of strategies with required fields.",
                model=self.model,
            )
            payload = extract_json(result)
            plans = [ClusterPlan.model_validate(x) for x in payload]
            deduped = self._dedupe(plans)
            if deduped:
                return deduped
        except Exception as exc:
            logger.exception("ContentStrategistAgent LLM path failed, using fallback: %s", exc)

        return self._fallback(input_clusters)

    @staticmethod
    def _dedupe(plans: list[ClusterPlan]) -> list[ClusterPlan]:
        seen_topics: set[str] = set()
        out: list[ClusterPlan] = []
        for p in plans:
            key = p.blog_topic.strip().lower()
            if key in seen_topics:
                continue
            seen_topics.add(key)
            out.append(p)
        return out

    @staticmethod
    def _fallback(clusters: list[dict[str, Any]]) -> list[ClusterPlan]:
        plans: list[ClusterPlan] = []
        for c in clusters:
            problem = c.get("problem", "Users are facing execution bottlenecks")
            audience = c.get("audience", "digital creators")
            emotion = c.get("emotion", "frustrated")
            topic = f"How {audience} can solve: {problem[:80]}"
            plans.append(
                ClusterPlan(
                    cluster_hash=c["cluster_hash"],
                    blog_topic=topic,
                    target_audience=audience,
                    content_angle=f"Actionable playbook focused on {emotion} users who need immediate wins.",
                    hook=f"Most {audience} repeat this mistake when tackling '{problem[:70]}'.",
                    cta="Reply with your exact bottleneck to get a tailored action checklist.",
                    seo_keywords=[
                        problem.split(" ")[0].lower(),
                        audience.replace(" ", "-").lower(),
                        "practical-guide",
                    ],
                )
            )
        return ContentStrategistAgent._dedupe(plans)
