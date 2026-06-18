import asyncio
from importlib.metadata import version

import typer

from crawler.crawler import run_crawl
from crawler.url import is_valid_url

app = typer.Typer()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"crawler {version('crawler')}")
        raise typer.Exit()


def _validate_url(url: str) -> str:
    if not is_valid_url(url):
        raise typer.BadParameter(f"Invalid URL: {url}")
    return url


@app.command()
def crawl(
    url: str = typer.Argument(..., callback=_validate_url, help="URL to crawl"),
    concurrency: int = typer.Option(10, "--concurrency", "-c", help="Max concurrent requests"),
    max_pages: int = typer.Option(0, "--max-pages", "-m", help="Max pages (0 = unlimited)"),
    delay: float = typer.Option(0.2, "--delay", "-d", help="Politeness delay in seconds"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    max_time: float | None = typer.Option(None, "--max-time", help="Max crawl time in seconds"),
    max_retries: int = typer.Option(3, "--max-retries", help="Max retries per URL"),
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version and exit"
    ),
):
    """Crawl a website and extract all linked pages."""
    result = asyncio.run(
        run_crawl(
            url,
            concurrency=concurrency,
            max_pages=max_pages,
            delay=delay,
            verbose=verbose,
            max_time=max_time,
            max_retries=max_retries,
        )
    )
    raise typer.Exit(code=result.status.value)
