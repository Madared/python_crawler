from __future__ import annotations

import asyncio

from crawler.crawler._context import CrawlerContext
from crawler.crawler._dispatcher import WorkDispatcher
from crawler.crawler._logger import CrawlLogger
from crawler.crawler._types import CrawlResult, CrawlStatus


class WorkerPool:
    def __init__(self, ctx: CrawlerContext, dispatch: WorkDispatcher) -> None:
        self._ctx = ctx
        self._dispatch = dispatch

    async def _run_worker(self) -> None:
        while not self._ctx.shutdown_event.is_set():
            url = await self._ctx.frontier.next_url()
            if url is None:
                break
            await self._dispatch.work(url)

    async def run(self) -> CrawlResult:
        workers = [
            asyncio.create_task(self._run_worker()) for _ in range(self._ctx._options.concurrency)
        ]

        if self._ctx._options.max_time is not None:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*workers),
                    timeout=self._ctx._options.max_time,
                )
            except TimeoutError:
                self._ctx.shutdown_event.set()
                await asyncio.gather(*workers, return_exceptions=True)
                CrawlLogger.print_summary(self._ctx.frontier.stats)
                return CrawlResult(
                    status=CrawlStatus.PARTIAL,
                    stats=self._ctx.frontier.stats,
                )
        else:
            await asyncio.gather(*workers)

        CrawlLogger.print_summary(self._ctx.frontier.stats)

        if self._ctx.frontier.stats.failed > 0:
            return CrawlResult(
                status=CrawlStatus.PARTIAL,
                stats=self._ctx.frontier.stats,
            )
        return CrawlResult(
            status=CrawlStatus.SUCCESS,
            stats=self._ctx.frontier.stats,
        )
