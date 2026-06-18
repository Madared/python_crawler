from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from crawler.crawler._types import DispatcherAsync, DispatcherConfig, DispatcherDeps
from crawler.parser import extract_links


class WorkDispatcher:
    def __init__(
        self,
        deps: DispatcherDeps,
        config: DispatcherConfig,
        async_ctx: DispatcherAsync,
    ) -> None:
        self._deps = deps
        self._config = config
        self._async_ctx = async_ctx

    async def work(self, url: str) -> None:
        path = urlparse(url).path or "/"
        if not self._config.robots_rules.is_allowed(path):
            self._deps.frontier.mark_done(url, success=True)
            self._deps.logger.page_skipped(self._deps.frontier.stats)
            return

        result = await self._deps.fetcher.fetch(url)

        links: list[str] = []
        if result.html and result.error is None:
            links = extract_links(result.html, result.final_url)
            for link in links:
                await self._deps.frontier.add_url(link)

        is_success = result.error is None and result.status_code < 400
        self._deps.frontier.mark_done(url, success=is_success)

        await self._deps.storage.save(result)

        async with self._async_ctx.output_lock:
            self._deps.logger.page_fetched(
                result.status_code, result.final_url, links, result.error
            )
            self._deps.logger.progress(self._deps.frontier.stats)

        if result.error is None:
            await asyncio.sleep(self._config.delay)
