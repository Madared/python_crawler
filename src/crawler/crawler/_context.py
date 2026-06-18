from __future__ import annotations

import asyncio
import logging
import signal

import httpx

from crawler.crawler._types import CrawlerOptions
from crawler.fetcher import RetryFetcher
from crawler.frontier import Frontier
from crawler.robotstxt import RobotsTxtRules

logger = logging.getLogger(__name__)


class CrawlerContext:
    def __init__(
        self,
        domain: str,
        frontier: Frontier,
        client: httpx.AsyncClient,
        fetcher: RetryFetcher,
        shutdown_event: asyncio.Event,
        output_lock: asyncio.Lock,
        robots_rules: RobotsTxtRules,
        effective_delay: float,
        options: CrawlerOptions,
        signal_handler_registered: bool = True,
    ) -> None:
        self.domain = domain
        self.frontier = frontier
        self.client = client
        self.fetcher = fetcher
        self.shutdown_event = shutdown_event
        self.output_lock = output_lock
        self.robots_rules = robots_rules
        self.effective_delay = effective_delay
        self._options = options
        self._signal_handler_registered = signal_handler_registered

    @property
    def options(self) -> CrawlerOptions:
        return self._options

    async def close(self) -> None:
        await self.client.aclose()
        if not self._signal_handler_registered:
            return
        self._signal_handler_registered = False
        try:
            loop = asyncio.get_running_loop()
            loop.remove_signal_handler(signal.SIGINT)
        except RuntimeError:
            logger.warning("Cannot remove SIGINT handler: no running event loop")
