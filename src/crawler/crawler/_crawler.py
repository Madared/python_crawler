from __future__ import annotations

import asyncio
import signal
from urllib.parse import urlparse

import httpx

from crawler.crawler._dispatcher import WorkDispatcher
from crawler.crawler._logger import CrawlLogger
from crawler.crawler._storage import DummyStorage, Storage
from crawler.crawler._types import (
    CrawlerOptions,
    CrawlResult,
    CrawlStatus,
    DispatcherAsync,
    DispatcherConfig,
    DispatcherDeps,
)
from crawler.fetcher import Fetcher, RetryFetcher, SimpleFetcher
from crawler.frontier import Frontier, FrontierStats
from crawler.robotstxt import RobotsTxtRules, parse_robots_txt


class Crawler:
    def __init__(self, options: CrawlerOptions, storage: Storage | None = None) -> None:
        self._options = options
        self._storage = storage or DummyStorage()

    async def _fetch_robots(
        self,
        client: httpx.AsyncClient,
        domain: str,
    ) -> tuple[RobotsTxtRules, float]:
        robots_url = f"https://{domain}/robots.txt"
        try:
            robots_response = await client.get(robots_url)
            robots_rules = parse_robots_txt(robots_response.text)
        except Exception:
            robots_rules = RobotsTxtRules()

        effective_delay = robots_rules.get_crawl_delay(self._options.delay)
        return robots_rules, effective_delay

    @staticmethod
    async def _run_worker_loop(
        dispatch: WorkDispatcher,
        frontier: Frontier,
        shutdown_event: asyncio.Event,
    ) -> None:
        while not shutdown_event.is_set():
            url = await frontier.next_url()
            if url is None:
                break
            await dispatch.work(url)

    async def _run_workers(
        self,
        frontier: Frontier,
        fetcher: Fetcher,
        shutdown_event: asyncio.Event,
        output_lock: asyncio.Lock,
        robots_rules: RobotsTxtRules,
        effective_delay: float,
    ) -> CrawlResult:
        logger = CrawlLogger(verbose=self._options.verbose)
        deps = DispatcherDeps(
            frontier=frontier,
            fetcher=fetcher,
            logger=logger,
            storage=self._storage,
        )
        config = DispatcherConfig(
            delay=effective_delay,
            robots_rules=robots_rules,
        )
        async_ctx = DispatcherAsync(
            output_lock=output_lock,
            shutdown_event=shutdown_event,
        )
        dispatch = WorkDispatcher(deps, config, async_ctx)

        workers = [
            asyncio.create_task(self._run_worker_loop(dispatch, frontier, shutdown_event))
            for _ in range(self._options.concurrency)
        ]

        if self._options.max_time is not None:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*workers),
                    timeout=self._options.max_time,
                )
            except TimeoutError:
                shutdown_event.set()
                await asyncio.gather(*workers, return_exceptions=True)
                CrawlLogger.print_summary(frontier.stats)
                return CrawlResult(
                    status=CrawlStatus.PARTIAL,
                    stats=frontier.stats,
                )
        else:
            await asyncio.gather(*workers)

        CrawlLogger.print_summary(frontier.stats)

        if frontier.stats.failed > 0:
            return CrawlResult(status=CrawlStatus.PARTIAL, stats=frontier.stats)
        return CrawlResult(status=CrawlStatus.SUCCESS, stats=frontier.stats)

    async def run_crawl(self, seed_url: str) -> CrawlResult:
        domain = urlparse(seed_url).hostname
        if not domain:
            return CrawlResult(status=CrawlStatus.FATAL, stats=FrontierStats())

        frontier = Frontier(seed_url, domain, self._options.max_pages)
        shutdown_event = asyncio.Event()
        output_lock = asyncio.Lock()

        client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            max_redirects=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Crawler/1.0)"},
        )
        fetcher = RetryFetcher(
            SimpleFetcher(client=client),
            max_retries=self._options.max_retries,
            verbose=self._options.verbose,
        )

        loop = asyncio.get_running_loop()

        def _on_sigint() -> None:
            shutdown_event.set()

        loop.add_signal_handler(signal.SIGINT, _on_sigint)

        robots_rules, effective_delay = await self._fetch_robots(client, domain)

        try:
            return await self._run_workers(
                frontier, fetcher, shutdown_event, output_lock, robots_rules, effective_delay
            )
        finally:
            await self._storage.close()
            await client.aclose()
            try:
                loop.remove_signal_handler(signal.SIGINT)
            except (RuntimeError, ValueError):
                pass
