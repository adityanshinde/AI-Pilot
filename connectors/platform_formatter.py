from __future__ import annotations

import re
from typing import Iterable


class PlatformFormatter:
    @staticmethod
    def to_blog_html(markdown_like: str) -> str:
        lines = [line.strip() for line in markdown_like.splitlines() if line.strip()]
        html_chunks: list[str] = []
        for line in lines:
            if line.startswith("### "):
                html_chunks.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                html_chunks.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                html_chunks.append(f"<h1>{line[2:]}</h1>")
            else:
                html_chunks.append(f"<p>{line}</p>")
        return "\n".join(html_chunks)

    @staticmethod
    def to_reddit_post(text: str, max_len: int = 39000) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3].rstrip() + "..."

    @staticmethod
    def to_threads_post(text: str, hashtags: Iterable[str], max_len: int = 500) -> str:
        cleaned_tags = []
        for tag in hashtags:
            t = re.sub(r"[^a-zA-Z0-9]", "", tag)
            if t:
                cleaned_tags.append(f"#{t[:20]}")

        tag_text = " ".join(cleaned_tags)
        base = text.strip()
        if tag_text:
            base = f"{base}\n\n{tag_text}".strip()

        if len(base) <= max_len:
            return base
        return base[: max_len - 3].rstrip() + "..."
