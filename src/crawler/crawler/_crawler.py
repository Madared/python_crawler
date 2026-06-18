from __future__ import annotations

from crawler.crawler._dispatcher import WorkDispatcher
from crawler.crawler._factory import create_crawler_context
from crawler.crawler._logger import CrawlLogger
from crawler.crawler._pool import WorkerPool
from crawler.crawler._storage import DummyStorage, Storage
from crawler.crawler._types import (
    CrawlerOptions,
    CrawlResult,
    CrawlStatus,
    DispatcherAsync,
    DispatcherConfig,
    DispatcherDeps,
)
from crawler.frontier import FrontierStats


class Crawler:
    def __init__(self, options: CrawlerOptions, storage: Storage | None = None) -> None:
        self._options = options
        self._storage = storage or DummyStorage()

    async def run_crawl(self, seed_url: str) -> CrawlResult:
        try:
            ctx = await create_crawler_context(seed_url, self._options)
        except ValueError:
            return CrawlResult(status=CrawlStatus.FATAL, stats=FrontierStats())

        try:
            logger = CrawlLogger(verbose=self._options.verbose)
            dispatch = WorkDispatcher(
                deps=DispatcherDeps(
                    frontier=ctx.frontier,
                    fetcher=ctx.fetcher,
                    logger=logger,
                    storage=self._storage,
                ),
                config=DispatcherConfig(
                    delay=ctx.effective_delay,
                    robots_rules=ctx.robots_rules,
                ),
                async_ctx=DispatcherAsync(
                    output_lock=ctx.output_lock,
                    shutdown_event=ctx.shutdown_event,
                ),
            )
            pool = WorkerPool(ctx, dispatch)
            return await pool.run()
        finally:
            await self._storage.close()
            await ctx.close()
