from __future__ import annotations

import typer

from crawler.frontier import FrontierStats


class CrawlLogger:
    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose

    def page_fetched(
        self,
        status_code: int,
        final_url: str,
        links: list[str],
        error: str | None,
    ) -> None:
        if error:
            typer.echo(f"ERROR {final_url} [{error}]", err=True)
        elif self._verbose:
            typer.echo(f"{status_code} {final_url}")
            for link in links:
                typer.echo(f"  -> {link}")

    def progress(self, stats: FrontierStats) -> None:
        if not self._verbose:
            return
        typer.echo(
            f"  [{stats.visited} visited / {stats.discovered} discovered / {stats.failed} failed]",
            err=True,
        )

    @staticmethod
    def print_summary(stats: FrontierStats) -> None:
        failed_part = f", {stats.failed} failed" if stats.failed > 0 else ""
        typer.echo(f"Crawl complete: {stats.visited} pages{failed_part}")
