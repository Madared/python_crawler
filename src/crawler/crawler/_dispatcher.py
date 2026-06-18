from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from crawler.crawler._logger import CrawlLogger
from crawler.crawler._storage import Storage
from crawler.fetcher import Fetcher
from crawler.frontier import Frontier
from crawler.parser import extract_links
from crawler.robotstxt import RobotsTxtRules


class WorkDispatcher:
    def __init__(
        self,
        frontier: Frontier,
        fetcher: Fetcher,
        delay: float,
        output_lock: asyncio.Lock,
        shutdown_event: asyncio.Event,
        robots_rules: RobotsTxtRules,
        logger: CrawlLogger,
        storage: Storage,
    ) -> None:
        self._frontier = frontier
        self._fetcher = fetcher
        self._delay = delay
        self._output_lock = output_lock
        self._shutdown_event = shutdown_event
        self._robots_rules = robots_rules
        self._logger = logger
        self._storage = storage

    async def work(self, url: str) -> None:
        path = urlparse(url).path or "/"
        if not self._robots_rules.is_allowed(path):
            self._frontier.mark_done(url, success=True)
            self._logger.page_skipped(self._frontier.stats)
            return

        result = await self._fetcher.fetch(url)

        links: list[str] = []
        if result.html and result.error is None:
            links = extract_links(result.html, result.final_url)
            for link in links:
                await self._frontier.add_url(link)

        is_success = result.error is None and result.status_code < 400
        self._frontier.mark_done(url, success=is_success)

        await self._storage.save(result)

        async with self._output_lock:
            self._logger.page_fetched(result.status_code, result.final_url, links, result.error)
            self._logger.progress(self._frontier.stats)

        if result.error is None:
            await asyncio.sleep(self._delay)
