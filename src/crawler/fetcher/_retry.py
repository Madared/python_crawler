from __future__ import annotations

import asyncio
import random

import typer

from crawler.fetcher._base import Fetcher
from crawler.fetcher._types import FetchResult


class RetryFetcher(Fetcher):
    def __init__(self, fetcher: Fetcher, max_retries: int = 3, verbose: bool = False):
        self._fetcher = fetcher
        self._max_retries = max_retries
        self._verbose = verbose

    async def fetch(self, url: str) -> FetchResult:
        for attempt in range(self._max_retries + 1):
            result = await self._fetcher.fetch(url)
            if result.error is None and result.status_code != 429:
                return result
            if attempt == self._max_retries:
                return result
            backoff = random.uniform(0, 2**attempt)
            if self._verbose:
                typer.echo(
                    f"  Retry {attempt + 1}/{self._max_retries} for {url}",
                    err=True,
                )
            await asyncio.sleep(backoff)
