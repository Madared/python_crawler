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

### `crawler/fetcher/`

HTTP fetching with connection pooling and error handling.

- **`Fetcher`** — wraps an `httpx.AsyncClient` with configurable response size limits. `fetch(url)` returns a `FetchResult` with the HTML content (decoded only for `text/html` responses), the final URL after redirects, and any transport error (timeout, DNS failure, SSL error, etc.). Non-HTML content types are detected but not decoded.
- **`FetchResult`** — dataclass with `status_code`, `html`, `final_url`, `content_type`, and `error`.

### `crawler/frontier/`

Crawl state management — tracks which URLs are discovered, in progress, and visited.

- **`Frontier`** — manages the URL queue with async-safe FIFO ordering, O(1) dedup (via visited/in-progress/queued sets), domain scoping, and max-pages limit. Exhaustion signaling via `asyncio.Event` ensures workers only stop when the queue is empty AND no workers are actively processing (prevents the queue-empty-but-work-in-flight race condition). `add_url` feeds URLs in, `next_url` returns the next URL to crawl (racing queue vs exhaustion), `mark_done` signals completion.
- **`FrontierStats`** — dataclass with `discovered`, `visited`, and `failed` counts.

## Getting Started

```bash
uv run crawler --help
```

## Setup and Testing

```bash
# Install dependencies and build the package
uv sync --all-extras

# Run tests
uv run pytest tests/

# Run linter
uv run ruff check src/
```
