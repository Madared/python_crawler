from __future__ import annotations

from abc import ABC, abstractmethod

from crawler.fetcher import FetchResult


class Storage(ABC):
    @abstractmethod
    async def save(self, result: FetchResult) -> None: ...

    async def close(self) -> None: ...


class DummyStorage(Storage):
    async def save(self, result: FetchResult) -> None:
        pass
