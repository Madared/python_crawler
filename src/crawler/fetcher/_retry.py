from __future__ import annotations

import asyncio
import logging
import random

from crawler.fetcher._base import Fetcher
from crawler.fetcher._types import FetchResult

logger = logging.getLogger(__name__)


class RetryFetcher(Fetcher):
    def __init__(self, fetcher: Fetcher, max_retries: int = 3):
        self._fetcher = fetcher
        self._max_retries = max_retries

    async def fetch(self, url: str) -> FetchResult:
        for attempt in range(self._max_retries + 1):
            result = await self._fetcher.fetch(url)
            if result.error is None and result.status_code != 429:
                return result
            if attempt == self._max_retries:
                return result
            backoff = random.uniform(0, 2**attempt)
            logger.info("Retry %d/%d for %s", attempt + 1, self._max_retries, url)
            await asyncio.sleep(backoff)
