from __future__ import annotations

import json
import logging
from pathlib import Path

from agents.schemas import ClusterPlan, GeneratedContentBundle
from utils.llm import extract_json, run_crewai_task

logger = logging.getLogger(__name__)


class ContentGeneratorAgent:
    """Generates blog, Reddit, and Threads content for each strategy."""

    def __init__(self, *, model: str, prompt_path: str = "prompts/content_generator_prompt.txt") -> None:
        self.model = model
        self.prompt_text = Path(prompt_path).read_text(encoding="utf-8")

    def run(self, plans: list[ClusterPlan]) -> list[GeneratedContentBundle]:
        bundles: list[GeneratedContentBundle] = []
        for plan in plans:
            try:
                description = (
                    f"{self.prompt_text}\n\n"
                    f"Input strategy:\n{plan.model_dump_json(indent=2)}\n\n"
                    "Return only JSON object with blog_content, reddit_content, threads_content."
                )
                result = run_crewai_task(
                    role="Content Generator",
                    goal="Generate high-quality multi-platform content from strategy plans.",
                    backstory="Expert copywriter in SEO, social storytelling, and short-form growth posts.",
                    description=description,
                    expected_output="JSON object with three platform outputs.",
                    model=self.model,
                )
                payload = extract_json(result)
                bundle = GeneratedContentBundle(
                    cluster_hash=plan.cluster_hash,
                    topic=plan.blog_topic,
                    target_audience=plan.target_audience,
                    angle=plan.content_angle,
                    hook=plan.hook,
                    cta=plan.cta,
                    seo_keywords=plan.seo_keywords,
                    blog_content=payload["blog_content"],
                    reddit_content=payload["reddit_content"],
                    threads_content=payload["threads_content"],
                )
                bundles.append(bundle)
            except Exception as exc:
                logger.exception("ContentGeneratorAgent LLM path failed, using fallback: %s", exc)
                bundles.append(self._fallback(plan))
        return bundles

    @staticmethod
    def _fallback(plan: ClusterPlan) -> GeneratedContentBundle:
        keyword_line = ", ".join(plan.seo_keywords or ["problem solving", "content strategy", "growth"]) 
        blog = f"""# {plan.blog_topic}

## Why this problem keeps showing up
{plan.hook}

Teams and solo creators repeatedly encounter this issue because they jump into tactics before they diagnose root causes. The result is wasted effort, inconsistent outcomes, and rising frustration.

## What this pain point actually means
When users describe this problem, they usually mean they lack a repeatable system. They need a process that moves from signal collection to prioritization to execution.

## Step 1: Capture high-signal user pain
Start with high-intent channels where users describe what is blocking progress. Extract exact wording, context, and urgency indicators.

## Step 2: Prioritize by frequency and emotional weight
Rank issues using two dimensions: how often the pain appears and how strong the emotional signal is.

## Step 3: Build a content angle that resolves the pain
Use one concrete promise per piece of content. Keep the scope narrow and useful.

## Step 4: Format for each platform without changing the core message
Use one source insight, then adapt structure and tone to platform constraints.

## Step 5: Measure and feed results back into the next cycle
Track saves, comments, and click-through to understand which problem statements resonate.

## SEO keywords used naturally
{keyword_line}

## Final takeaway
A content engine works when it treats audience pain as a dynamic signal, not a one-time research task. Build the workflow once, then iterate every cycle.

{plan.cta}
"""

        reddit = (
            f"{plan.hook}\n\n"
            f"I keep seeing this with {plan.target_audience}. Everyone is working hard, but the strategy breaks because the process is reactive. "
            "What changed results for me was creating a fixed loop: collect real pain points, cluster them, then publish one specific solution per cluster. "
            f"If anyone here is dealing with this, I can share the exact checklist I use. {plan.cta}"
        )

        threads = (
            f"{plan.hook}\n"
            "Most content misses because it starts with ideas, not pain.\n"
            "Use this sequence: collect -> cluster -> prioritize -> publish -> learn.\n"
            f"{plan.cta}"
        )

        return GeneratedContentBundle(
            cluster_hash=plan.cluster_hash,
            topic=plan.blog_topic,
            target_audience=plan.target_audience,
            angle=plan.content_angle,
            hook=plan.hook,
            cta=plan.cta,
            seo_keywords=plan.seo_keywords,
            blog_content=blog,
            reddit_content=reddit,
            threads_content=threads,
        )
