from __future__ import annotations

import re
from typing import Iterable

NOISE_PATTERNS = [
    re.compile(r"https?://\\S+", re.IGNORECASE),
    re.compile(r"www\\.\\S+", re.IGNORECASE),
    re.compile(r"\\s+"),
]

EMOJI_PATTERN = re.compile(
    "["
    "\\U0001F600-\\U0001F64F"
    "\\U0001F300-\\U0001F5FF"
    "\\U0001F680-\\U0001F6FF"
    "\\U0001F1E0-\\U0001F1FF"
    "\\U00002700-\\U000027BF"
    "\\U000024C2-\\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def clean_text(text: str) -> str:
    cleaned = EMOJI_PATTERN.sub(" ", text or "")
    for pattern in NOISE_PATTERNS:
        replacement = " " if pattern.pattern != r"\\s+" else " "
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned.strip()


def keyword_match_count(text: str, keywords: Iterable[str]) -> int:
    lowered = text.lower()
    return sum(1 for kw in keywords if kw.lower() in lowered)


def compact_whitespace(text: str) -> str:
    return re.sub(r"\\s+", " ", text).strip()
