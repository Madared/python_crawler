# Crawler

A web crawler project built as part of a job interview process for **Zego**.

## Tech Stack

- **Python 3.12+**
- **typer** – CLI framework
- **httpx** – async HTTP client
- **beautifulsoup4** + **lxml** – HTML parsing
- **pytest** / **pytest-asyncio** / **respx** – testing
- **ruff** – linting
- **uv** – package management

## CLI Usage

```bash
uv run crawler --help
uv run crawler https://example.com
uv run crawler https://example.com --concurrency 20 --max-pages 100
uv run crawler https://example.com --verbose --max-time 30
```

### Options

| Option | Default | Description |
|---|---|---|
| `URL` | (required) | Seed URL to crawl |
| `--concurrency`, `-c` | `10` | Max concurrent requests |
| `--max-pages`, `-m` | `0` | Max pages to crawl (`0` = unlimited) |
| `--delay`, `-d` | `0.2` | Politeness delay in seconds between requests |
| `--verbose`, `-v` | `False` | Print progress to stderr |
| `--max-time` | (none) | Max crawl duration in seconds |
| `--max-retries` | `3` | Max retries per URL (exponential backoff) |
| `--version` | | Show version and exit |
| `--help` | | Show usage and exit |

### Output format

```
200 https://example.com/
  -> https://example.com/page1
  -> https://example.com/page2
200 https://example.com/page1
ERROR https://example.com/broken [Connection refused]
```

Status codes and final URLs go to stdout. Errors and verbose progress go to stderr, allowing clean pipelining: `./crawler https://example.com > results.txt`.

## Setup and Testing

```bash
# Install dependencies and build the package
uv sync --all-extras

# Run tests
uv run pytest tests/

# Run linter
uv run ruff check src/
```

## Modules

### `crawler/url/`

URL normalization, resolution, validation, and domain matching.

- **`normalize_url`** — canonical form for dedup: lowercase scheme+host, default port removal, trailing slash normalization, dot-segment removal, query parameter sorting, percent-encoding normalization
- **`resolve_url`** — resolves relative URLs against a base; returns `None` for non-`http(s)` schemes
- **`is_valid_url`** — checks for a valid scheme and hostname
- **`is_same_domain`** — exact hostname match, case-insensitive, port ignored

### `crawler/parser/`

HTML link extraction.

- **`extract_links`** — parses HTML with BeautifulSoup + lxml, collects all `<a href>` links, resolves them against the base URL (respecting `<base>` tags), deduplicates by first occurrence. Skips fragment-only, empty/whitespace-only, and non-`http(s)` links.

### `crawler/robotstxt/`

robots.txt parsing.

- **`parse_robots_txt`** — parses robots.txt content for a given user-agent. Strips comments, matches the applicable rule group (exact UA or `*` fallback), and returns a `RobotsTxtRules` object.
- **`RobotsTxtRules`** — query interface with `is_allowed(path)` to check if a URL path is permitted, and `get_crawl_delay(default)` to get the effective politeness delay (respects `Crawl-Delay` as the minimum floor).

> **Note:** robots.txt is fetched using the same scheme as the seed URL (HTTP or HTTPS). If the fetch fails for any reason (timeout, DNS failure, etc.), the crawler falls back to allowing all paths.

### `crawler/fetcher/`

HTTP fetching with connection pooling, retry logic, and error handling.

- **`Fetcher`** — ABC defining the `fetch(url)` interface.
- **`SimpleFetcher`** — concrete implementation wrapping an `httpx.AsyncClient` with configurable response size limits. `fetch(url)` returns a `FetchResult` with the HTML content (decoded only for `text/html` responses), the final URL after redirects, and any transport error (timeout, DNS failure, SSL error, etc.). Non-HTML content types are detected but not decoded.
- **`RetryFetcher`** — decorator wrapping any `Fetcher` with full-jitter exponential backoff. Retries on transport errors and HTTP 429 responses. Logs retry attempts via Python's `logging` module.
- **`FetchResult`** — dataclass with `status_code`, `html`, `final_url`, `content_type`, and `error`.

### `crawler/frontier/`

Crawl state management — tracks which URLs are discovered, in progress, and visited.

- **`Frontier`** — manages the URL queue with async-safe FIFO ordering, O(1) dedup (via visited/in-progress/queued sets), domain scoping, and max-pages limit. Exhaustion signaling via `asyncio.Event` ensures workers only stop when the queue is empty AND no workers are actively processing (prevents the queue-empty-but-work-in-flight race condition). `add_url` (synchronous) feeds URLs in, `next_url` returns the next URL to crawl (racing queue vs exhaustion), `mark_done` signals completion.
- **`FrontierStats`** — dataclass with `discovered`, `visited`, and `failed` counts.

### `crawler/crawler/`

Crawl orchestrator — wires the fetcher, parser, and frontier together.

- **`run_crawl`** — async function that runs a full crawl. Creates workers that loop: `next_url` → `fetch` → `extract_links` → `add_url` → `mark_done`. Handles concurrency, politeness delay, graceful shutdown on SIGINT, and client cleanup. Returns a `CrawlResult`.
- **`Crawler`** — standalone class that accepts `CrawlerOptions` and an optional `Storage` implementation. `run_crawl(seed_url)` orchestrates context creation, worker pool execution, and cleanup.
- **`CrawlResult`** — dataclass with `status` (`CrawlStatus.SUCCESS`, `CrawlStatus.PARTIAL`, or `CrawlStatus.FATAL`) and `stats` (`FrontierStats` with `discovered`, `visited`, `failed` counts).
- **`Storage`** — ABC for persisting fetch results. `save(result)` stores a page; `close()` cleans up resources.
- **`DummyStorage`** — no-op `Storage` implementation used by default. Inject a custom `Storage` to persist results.
- **`WorkerPool`** — manages concurrent worker tasks. Handles worker crashes gracefully (failed URLs are marked and the crawl continues). Supports `max_time` timeout.
- **`WorkDispatcher`** — dispatches work for a single URL: checks robots.txt, fetches, extracts links, marks done, and stores results.

### `crawler/cli.py`

CLI entry point. Defines the `crawl` command with all user-facing options.

- **`crawl`** — runs the crawler from the command line. Required `URL` argument, validated on input. Options: `--concurrency` (10), `--max-pages` (0 = unlimited), `--delay` (0.2s), `--verbose`, `--max-time`, `--max-retries` (3), `--version`, `--help`.
