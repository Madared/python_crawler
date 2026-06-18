from __future__ import annotations

from abc import ABC, abstractmethod

from crawler.fetcher._types import FetchResult


class Fetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> FetchResult: ...
