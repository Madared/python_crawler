from __future__ import annotations

import asyncio
import signal
from dataclasses import dataclass
from enum import IntEnum
from urllib.parse import urlparse

import httpx
import typer

from crawler.fetcher import Fetcher
from crawler.frontier import Frontier, FrontierStats
from crawler.parser import extract_links


class CrawlStatus(IntEnum):
    SUCCESS = 0
    PARTIAL = 1
    FATAL = 2


@dataclass
class CrawlResult:
    status: CrawlStatus
    stats: FrontierStats


def _print_result(
    status_code: int,
    final_url: str,
    links: list[str],
    error: str | None,
) -> None:
    if error:
        typer.echo(f"ERROR {final_url} [{error}]", err=True)
    else:
        typer.echo(f"{status_code} {final_url}")
        for link in links:
            typer.echo(f"  -> {link}")


async def _worker(
    frontier: Frontier,
    fetcher: Fetcher,
    delay: float,
    output_lock: asyncio.Lock,
    shutdown_event: asyncio.Event,
) -> None:
    while not shutdown_event.is_set():
        url = await frontier.next_url()
        if url is None:
            break

        result = await fetcher.fetch(url)

        links: list[str] = []
        if result.html and result.error is None:
            links = extract_links(result.html, result.final_url)
            for link in links:
                await frontier.add_url(link)

        is_success = result.error is None and result.status_code < 400
        frontier.mark_done(url, success=is_success)

        async with output_lock:
            _print_result(result.status_code, result.final_url, links, result.error)

        if result.error is None:
            await asyncio.sleep(delay)


async def run_crawl(
    seed_url: str,
    *,
    concurrency: int = 10,
    max_pages: int = 0,
    delay: float = 0.2,
    verbose: bool = False,
) -> CrawlResult:
    domain = urlparse(seed_url).hostname
    if not domain:
        return CrawlResult(status=CrawlStatus.FATAL, stats=FrontierStats())

    frontier = Frontier(seed_url, domain, max_pages)
    shutdown_event = asyncio.Event()
    output_lock = asyncio.Lock()

    client = httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        max_redirects=10,
        headers={"User-Agent": "Mozilla/5.0 (compatible; Crawler/1.0)"},
    )
    fetcher = Fetcher(client=client)

    loop = asyncio.get_running_loop()

    def _on_sigint() -> None:
        shutdown_event.set()

    loop.add_signal_handler(signal.SIGINT, _on_sigint)

    try:
        workers = [
            asyncio.create_task(_worker(frontier, fetcher, delay, output_lock, shutdown_event))
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)
    finally:
        await client.aclose()
        try:
            loop.remove_signal_handler(signal.SIGINT)
        except (RuntimeError, ValueError):
            pass

    if frontier.stats.failed > 0:
        return CrawlResult(status=CrawlStatus.PARTIAL, stats=frontier.stats)
    return CrawlResult(status=CrawlStatus.SUCCESS, stats=frontier.stats)
