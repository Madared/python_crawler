from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum

from crawler.crawler._logger import CrawlLogger
from crawler.crawler._storage import Storage
from crawler.fetcher import Fetcher
from crawler.frontier import Frontier, FrontierStats
from crawler.robotstxt import RobotsTxtRules


@dataclass
class DispatcherDeps:
    frontier: Frontier
    fetcher: Fetcher
    logger: CrawlLogger
    storage: Storage


@dataclass
class DispatcherConfig:
    delay: float
    robots_rules: RobotsTxtRules


@dataclass
class DispatcherAsync:
    output_lock: asyncio.Lock
    shutdown_event: asyncio.Event


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
