from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from crawler.frontier import FrontierStats


class CrawlStatus(IntEnum):
    SUCCESS = 0
    PARTIAL = 1
    FATAL = 2


@dataclass
class CrawlResult:
    status: CrawlStatus
    stats: FrontierStats


@dataclass
class CrawlerOptions:
    concurrency: int = 10
    max_pages: int = 0
    delay: float = 0.2
    verbose: bool = False
    max_time: float | None = None
    max_retries: int = 3
