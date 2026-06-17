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
