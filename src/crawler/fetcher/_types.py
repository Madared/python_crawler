from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FetchResult:
    status_code: int
    html: str | None
    final_url: str
    content_type: str
    error: str | None
