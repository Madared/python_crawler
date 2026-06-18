from __future__ import annotations

import asyncio
import signal
from urllib.parse import urlparse

import httpx

from crawler.crawler._context import CrawlerContext
from crawler.crawler._types import CrawlerOptions
from crawler.fetcher import RetryFetcher, SimpleFetcher
from crawler.frontier import Frontier
from crawler.robotstxt import RobotsTxtRules, parse_robots_txt


async def _fetch_robots(
    client: httpx.AsyncClient,
    domain: str,
    cli_delay: float,
) -> tuple[RobotsTxtRules, float]:
    robots_url = f"https://{domain}/robots.txt"
    try:
        response = await client.get(robots_url)
        rules = parse_robots_txt(response.text)
    except Exception:
        rules = RobotsTxtRules()
    return rules, rules.get_crawl_delay(cli_delay)


async def create_crawler_context(
    seed_url: str,
    options: CrawlerOptions,
) -> CrawlerContext:
    domain = urlparse(seed_url).hostname
    if not domain:
        raise ValueError(f"Invalid URL: {seed_url}")

    frontier = Frontier(seed_url, domain, options.max_pages)
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
        max_retries=options.max_retries,
        verbose=options.verbose,
    )

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, shutdown_event.set)

    robots_rules, effective_delay = await _fetch_robots(client, domain, options.delay)

    return CrawlerContext(
        domain=domain,
        frontier=frontier,
        client=client,
        fetcher=fetcher,
        shutdown_event=shutdown_event,
        output_lock=output_lock,
        robots_rules=robots_rules,
        effective_delay=effective_delay,
        options=options,
        signal_handler_registered=True,
    )
