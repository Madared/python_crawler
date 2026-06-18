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

With `--verbose`, per-page output goes to stdout:

```
200 https://example.com/
  -> https://example.com/page1
  -> https://example.com/page2
200 https://example.com/page1
ERROR https://example.com/broken [Connection refused]
```

Errors and verbose progress stats go to stderr. Without `--verbose`, only the summary line is printed to stdout (e.g., `Crawl complete: 5 pages`), allowing clean pipelining: `./crawler https://example.com > results.txt`.

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

## Design Decisions

### Architecture Patterns

**Strategy Pattern — Fetcher ABC**

The `Fetcher` abstract base class defines a single `fetch(url) -> FetchResult` contract. This allows swapping implementations without changing any downstream code:
- `SimpleFetcher` — the production HTTP client, wrapping `httpx.AsyncClient` with response size limits and content-type detection.
- `RetryFetcher` — a decorator wrapping any `Fetcher` with full-jitter exponential backoff, retrying on transport errors and HTTP 429 responses.
- Mock fetchers — used in tests to isolate worker/dispatcher logic from network behavior.

This pattern also enables future extensions: a caching fetcher (Redis-backed), a proxy-rotating fetcher, or a headless-browser fetcher for JavaScript-rendered pages — all without touching the crawler orchestrator.

**Strategy Pattern — Storage ABC**

The `Storage` ABC (`save(result)`, `close()`) decouples persistence from crawl logic. `DummyStorage` is the default no-op implementation. Injecting a custom `Storage` (PostgreSQL, S3, Elasticsearch) requires zero changes to the crawler itself. The `close()` lifecycle method ensures proper resource cleanup in all exit paths (success, timeout, crash, SIGINT).

**Single Responsibility — WorkerPool Separation**

The `WorkerPool` is deliberately separated from the `Crawler` orchestrator. This provides:
- **Exception isolation** — a crashed worker is caught and the URL is marked as failed; the crawl continues. Without this separation, an exception in one worker would propagate and kill all concurrent work.
- **Independent testability** — `WorkerPool` can be tested with a mock `WorkDispatcher` to verify crash handling, timeout behavior, and result construction without involving HTTP or HTML parsing.
- **Composability** — different pool strategies (fixed-size, dynamically scaling, priority-based) can be swapped in without changing the dispatcher or frontier.

**Dependency Injection**

All dependencies are passed explicitly — no global state, no singletons:
- `httpx.AsyncClient` is passed to `SimpleFetcher`, not created inside it.
- `Storage` is passed to `Crawler`, which passes it through to `WorkDispatcher`.
- `CrawlerContext` bundles shared async primitives (`Event`, `Lock`) and domain-scoped configuration (robots rules, politeness delay) for injection into `WorkerPool` and `WorkDispatcher`.

This makes testing trivial (inject mocks at any level) and composition straightforward (assemble different fetcher/storage/pool combinations).

**Observer-Like Pattern — CrawlLogger**

`CrawlLogger` receives events from `WorkDispatcher` (page fetched, page skipped, progress updates) and controls output based on the `verbose` flag. This can be extended with structured logging, Prometheus metrics, or webhook notifications without changing the dispatcher.

### Trade-offs

**Async vs Multi-threading**

Python's GIL makes multi-threading ineffective for CPU-bound parallelism, but web crawling is I/O-bound — the perfect use case for `asyncio`. Async provides:
- Thousands of concurrent connections with minimal memory overhead (coroutines vs threads).
- No thread-safety concerns for shared state (single-threaded event loop).
- Clean composition with `asyncio.gather`, `asyncio.wait`, and `asyncio.Queue`.

The trade-off: async code is harder to debug, and a blocking operation (e.g., synchronous DNS resolution) would stall the entire event loop. All I/O in this codebase is explicitly async to avoid this.

**Compiled Regex vs Procedural Checks for robots.txt Wildcards**

The robots.txt parser converts wildcard patterns (`*` for any characters, `$` for end-of-path) into compiled regex via `re.compile()` rather than writing manual procedural string checks. Compiled regex is implemented in C, handles edge cases correctly, and keeps the code concise. Writing equivalent logic by hand (splitting on `*`, checking prefixes and suffixes, handling `$` anchors) would be more verbose, harder to maintain, and more likely to have subtle bugs. The trade-off is that regex compilation happens once per rule at parse time, but this is negligible for the typical number of rules (dozens, not thousands).

**In-Memory Frontier vs Persistent Queue**

The `Frontier` keeps all state in memory (Python sets + `asyncio.Queue`). This is fast and simple but means crawl state is lost on crash. For production use, a persistent queue (Redis, SQLite) would allow pause/resume and recovery. The current design makes this straightforward — the `Frontier` interface (`next_url`, `add_url`, `mark_done`) could be backed by any storage backend.

**Synchronous `add_url`**

`Frontier.add_url` is synchronous (not `async`) because it only performs in-memory set checks and `Queue.put_nowait`. Making it async would add unnecessary overhead for a method that never awaits. This is called from `WorkDispatcher` inside the async event loop, but since it's non-blocking, it doesn't stall other coroutines.

**Per-Worker Delay vs Global Rate Limiting**

The current politeness delay (`--delay`) is applied per-worker after each successful fetch. This means the total request rate scales linearly with concurrency: with `--concurrency 10 --delay 0.2`, each worker sleeps 0.2s between requests (~5 req/s), resulting in ~50 requests per second total. For the single-domain use case this is acceptable, but increasing concurrency directly increases the total request rate, which can violate the spirit of politeness. A production crawler would separate concurrency (parallelism — how many in-flight requests) from rate limiting (politeness — total requests per second across all workers) using a shared token bucket or semaphore. This would allow high concurrency for throughput while keeping the global request rate respectful.

### Extending to Multiple Domains

The current architecture is domain-scoped by design: the `Frontier` filters URLs to a single domain, `robots.txt` rules are fetched per domain, and politeness delays are per-domain. This isolation is intentional — it prevents cross-domain contamination and respects each site's crawl rules independently.

To extend to multiple domains, the natural approach is a **domain multiplexer**:

1. **Shared connection pool** — a single `httpx.AsyncClient` with a large connection pool serves all domains efficiently.
2. **Per-domain frontiers** — each domain gets its own `Frontier` instance with independent `robots.txt` rules and rate limits.
3. **Domain router** — when a URL is discovered, the router checks its domain and dispatches it to the appropriate frontier. New domains dynamically spawn their own worker pools.
4. **Global concurrency cap** — a semaphore limits total concurrent requests across all domains to avoid overwhelming the connection pool or triggering anti-bot measures.

My `Storage` ABC already supports composing multiple crawlers — swapping `DummyStorage` for a shared database enables persistent state across domain crawls.

### Why CLI Isn't Ideal for Production

The CLI is sufficient for single-domain, ad-hoc crawls, but it has fundamental limitations for production use:

- **No job scheduling** — each invocation is a one-shot process. There's no way to queue crawls, set priorities, or schedule recurring crawls.
- **No progress monitoring** — once started, you can only watch stderr. There's no API to query crawl status, pause/resume, or get real-time metrics.
- **No persistent state** — if the process crashes, all discovered URLs are lost. There's no recovery mechanism.
- **No horizontal scaling** — a single CLI process is bound to one machine. Distributing work across machines requires a service architecture.
- **No multi-user access** — CLI is inherently single-user. A team needs a shared service with role-based access.

**Better alternatives:**
- **REST API with async job queue** — submit crawl jobs via HTTP, track progress via polling or WebSockets. Workers pull from a queue (Celery, RQ). My `Crawler` class is already decoupled from CLI — `run_crawl()` can be called from any context.
- **gRPC service** — for internal microservice communication, with streaming progress updates.

My code is already structured to support this transition: the CLI is a thin `typer` wrapper around `run_crawl()`, the `Storage` ABC can be swapped for PostgreSQL/S3, and `CrawlLogger` can be replaced with structured logging and metrics.

### Future Refinements (Time Constraints)

If not constrained by time, I would address the following:

- **Sitemap parsing** — parse `sitemap.xml` and `sitemap-index.xml` to seed the `Frontier` before link crawling begins. This discovers pages more efficiently (especially for large sites with deep link structures) and respects the site's own content hierarchy. Would be implemented as an optional pre-crawl step in `Crawler.run_crawl()`.

- **Real storage implementation** — a PostgreSQL-backed `Storage` that persists the URL graph (source URL → discovered URLs), raw HTML snapshots, and crawl timestamps. This enables pause/resume, deduplication across crawls, and historical analysis.

- **Integration test environment** — Docker-based test setup with a local HTTP server serving realistic HTML samples, mock DNS resolution, and a controlled robots.txt. This would enable end-to-end testing with semi-dynamic data (e.g., a server that returns different pages based on request count).

- **Structured output formats** — JSON, CSV, and NDJSON export options beyond the current stdout/stderr text format.

- **Rate limiting refinements** — per-domain request rate limiting using a token bucket algorithm, respecting both `Crawl-Delay` from robots.txt and server response times (adaptive delay based on `Retry-After` headers).

- **JavaScript rendering fallback** — integration with a headless browser (Playwright) for SPAs that require JavaScript execution to render links. Would be an optional `Fetcher` implementation, keeping the architecture clean.

- **Graceful pause/resume** — serializing the `Frontier` state (visited, queued, in-progress sets) to disk on SIGINT and reloading on restart.

### Development Workflow & Tools

- **IDE**: PyCharm.
- **AI assistance**: opencode using small models for speed and larger models for better design discussion, debugging and test generation . Total AI cost for this task was approximately $0.87.
- **Package management**: `uv` for fast dependency resolution and virtual environment management.
- **Linting & formatting**: `ruff` for both linting and formatting, configured with a 100-character line limit.
- **Testing**: `pytest` with `pytest-asyncio` for async test support, `respx` for HTTP mocking at the transport layer.
