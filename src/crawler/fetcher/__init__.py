from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class FetchResult:
    status_code: int
    html: str | None
    final_url: str
    content_type: str
    error: str | None


class Fetcher:
    def __init__(self, client: httpx.AsyncClient, max_response_size: int = 10 * 1024 * 1024):
        self._client = client
        self._max_response_size = max_response_size

    async def fetch(self, url: str) -> FetchResult:
        try:
            response = await self._client.get(url)
        except httpx.RequestError as e:
            return FetchResult(
                status_code=0,
                html=None,
                final_url=url,
                content_type="",
                error=str(e),
            )

        content_type = response.headers.get("content-type", "")
        final_url = str(response.url)

        if len(response.content) > self._max_response_size:
            truncated = response.content[: self._max_response_size]
            html = truncated.decode(response.encoding or "utf-8", errors="replace")
            error = f"Response truncated: exceeds {self._max_response_size} bytes"
        elif content_type.startswith("text/html"):
            html = response.text
            error = None
        else:
            html = None
            error = None

        return FetchResult(
            status_code=response.status_code,
            html=html,
            final_url=final_url,
            content_type=content_type,
            error=error,
        )
