from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PublishResult:
    platform: str
    status: str
    external_id: str | None = None
    error: str | None = None
