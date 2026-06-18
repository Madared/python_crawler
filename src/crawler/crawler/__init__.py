from crawler.crawler._crawler import Crawler
from crawler.crawler._types import CrawlerOptions, CrawlResult, CrawlStatus

__all__ = ["CrawlStatus", "CrawlResult", "CrawlerOptions", "Crawler", "run_crawl"]


async def run_crawl(
    seed_url: str,
    *,
    concurrency: int = 10,
    max_pages: int = 0,
    delay: float = 0.2,
    verbose: bool = False,
    max_time: float | None = None,
) -> CrawlResult:
    options = CrawlerOptions(
        concurrency=concurrency,
        max_pages=max_pages,
        delay=delay,
        verbose=verbose,
        max_time=max_time,
    )
    crawler = Crawler(options)
    return await crawler.run_crawl(seed_url)
