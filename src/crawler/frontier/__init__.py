from __future__ import annotations

import asyncio
from dataclasses import dataclass

from crawler.url import is_same_domain, is_valid_url, normalize_url


@dataclass
class FrontierStats:
    discovered: int = 0
    visited: int = 0
    failed: int = 0


class Frontier:
    def __init__(self, seed_url: str, domain: str, max_pages: int = 0):
        self._domain = domain
        self._max_pages = max_pages
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._visited: set[str] = set()
        self._in_progress: set[str] = set()
        self._queued: set[str] = set()
        self._active_workers = 0
        self._exhausted = asyncio.Event()
        self._stats = FrontierStats()

        seed = normalize_url(seed_url)
        self._queue.put_nowait(seed)
        self._queued.add(seed)
        self._stats.discovered += 1

    def add_url(self, url: str) -> bool:
        if not is_valid_url(url):
            return False

        if not is_same_domain(url, self._domain):
            return False

        normalized = normalize_url(url)

        if normalized in self._visited or normalized in self._queued:
            return False
        if normalized in self._in_progress:
            return False

        if self._max_pages > 0 and self._stats.discovered >= self._max_pages:
            return False

        was_empty = self._queue.empty()
        self._queue.put_nowait(normalized)
        self._queued.add(normalized)
        self._stats.discovered += 1

        if was_empty:
            self._exhausted.clear()

        return True

    async def next_url(self) -> str | None:
        get_task = asyncio.create_task(self._queue.get())
        wait_task = asyncio.create_task(self._exhausted.wait())

        done, pending = await asyncio.wait(
            [get_task, wait_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        if not get_task.done():
            return None

        url = get_task.result()
        self._queued.discard(url)
        self._active_workers += 1
        self._in_progress.add(url)
        return url

    def mark_done(self, url: str, success: bool = True):
        normalized = normalize_url(url)
        if normalized not in self._in_progress:
            return
        self._in_progress.discard(normalized)
        self._active_workers -= 1

        self._visited.add(normalized)
        self._stats.visited += 1
        if not success:
            self._stats.failed += 1

        if self._queue.empty() and self._active_workers == 0:
            self._exhausted.set()

    @property
    def exhausted(self) -> asyncio.Event:
        return self._exhausted

    @property
    def stats(self) -> FrontierStats:
        return self._stats
