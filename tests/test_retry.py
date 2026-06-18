from unittest.mock import AsyncMock, patch

import pytest

from crawler.fetcher import Fetcher, FetchResult, RetryFetcher


@pytest.fixture
def mock_fetcher():
    return AsyncMock(spec=Fetcher)


@pytest.fixture
def success_result():
    return FetchResult(
        status_code=200,
        html="<html></html>",
        final_url="https://example.com/",
        content_type="text/html",
        error=None,
    )


class TestRetryFetcher:
    async def test_success_first_attempt(self, mock_fetcher, success_result):
        mock_fetcher.fetch.return_value = success_result
        retry = RetryFetcher(mock_fetcher, max_retries=3)
        result = await retry.fetch("https://example.com/")
        assert result.status_code == 200
        assert result.error is None
        assert mock_fetcher.fetch.call_count == 1

    async def test_no_retry_on_404(self, mock_fetcher):
        result_404 = FetchResult(
            status_code=404,
            html="<html>Not Found</html>",
            final_url="https://example.com/not-found",
            content_type="text/html",
            error=None,
        )
        mock_fetcher.fetch.return_value = result_404
        retry = RetryFetcher(mock_fetcher, max_retries=3)
        result = await retry.fetch("https://example.com/not-found")
        assert result.status_code == 404
        assert mock_fetcher.fetch.call_count == 1

    async def test_no_retry_on_500(self, mock_fetcher):
        result_500 = FetchResult(
            status_code=500,
            html=None,
            final_url="https://example.com/error",
            content_type="text/html",
            error=None,
        )
        mock_fetcher.fetch.return_value = result_500
        retry = RetryFetcher(mock_fetcher, max_retries=3)
        result = await retry.fetch("https://example.com/error")
        assert result.status_code == 500
        assert mock_fetcher.fetch.call_count == 1

    async def test_retry_on_429(self, mock_fetcher, success_result):
        result_429 = FetchResult(
            status_code=429,
            html=None,
            final_url="https://example.com/",
            content_type="text/html",
            error="Rate limited",
        )
        mock_fetcher.fetch.side_effect = [result_429, success_result]
        retry = RetryFetcher(mock_fetcher, max_retries=3)
        result = await retry.fetch("https://example.com/")
        assert result.status_code == 200
        assert mock_fetcher.fetch.call_count == 2

    async def test_retry_on_transport_error(self, mock_fetcher, success_result):
        transport_error = FetchResult(
            status_code=0,
            html=None,
            final_url="https://example.com/",
            content_type="",
            error="Connection refused",
        )
        mock_fetcher.fetch.side_effect = [transport_error, success_result]
        retry = RetryFetcher(mock_fetcher, max_retries=3)
        result = await retry.fetch("https://example.com/")
        assert result.status_code == 200
        assert mock_fetcher.fetch.call_count == 2

    async def test_max_retries_exhausted(self, mock_fetcher):
        result_429 = FetchResult(
            status_code=429,
            html=None,
            final_url="https://example.com/",
            content_type="text/html",
            error="Rate limited",
        )
        mock_fetcher.fetch.return_value = result_429
        retry = RetryFetcher(mock_fetcher, max_retries=2)
        result = await retry.fetch("https://example.com/")
        assert result.status_code == 429
        assert mock_fetcher.fetch.call_count == 3

    async def test_backoff_delay(self, mock_fetcher, success_result):
        result_429 = FetchResult(
            status_code=429,
            html=None,
            final_url="https://example.com/",
            content_type="text/html",
            error="Rate limited",
        )
        mock_fetcher.fetch.side_effect = [result_429, success_result]
        retry = RetryFetcher(mock_fetcher, max_retries=3)

        with (
            patch("random.uniform", return_value=0.5),
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            result = await retry.fetch("https://example.com/")
            assert result.status_code == 200
            mock_sleep.assert_awaited_once_with(0.5)

    async def test_zero_retries_no_backoff(self, mock_fetcher):
        result_429 = FetchResult(
            status_code=429,
            html=None,
            final_url="https://example.com/",
            content_type="text/html",
            error="Rate limited",
        )
        mock_fetcher.fetch.return_value = result_429
        retry = RetryFetcher(mock_fetcher, max_retries=0)
        result = await retry.fetch("https://example.com/")
        assert result.status_code == 429
        assert mock_fetcher.fetch.call_count == 1

    async def test_retry_logs_info(self, mock_fetcher, success_result, caplog):
        result_429 = FetchResult(
            status_code=429,
            html=None,
            final_url="https://example.com/",
            content_type="text/html",
            error="Rate limited",
        )
        mock_fetcher.fetch.side_effect = [result_429, success_result]
        retry = RetryFetcher(mock_fetcher, max_retries=3)

        with (
            patch("random.uniform", return_value=0.01),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with caplog.at_level("INFO", logger="crawler.fetcher._retry"):
                result = await retry.fetch("https://example.com/")
            assert result.status_code == 200
            assert any("Retry" in record.message for record in caplog.records)

    async def test_multiple_retries(self, mock_fetcher, success_result):
        results = [
            FetchResult(429, None, "https://example.com/", "", "Rate limit"),
            FetchResult(429, None, "https://example.com/", "", "Rate limit"),
            FetchResult(0, None, "https://example.com/", "", "Timeout"),
            success_result,
        ]
        mock_fetcher.fetch.side_effect = results
        retry = RetryFetcher(mock_fetcher, max_retries=5)

        with (
            patch("random.uniform", return_value=0.01),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await retry.fetch("https://example.com/")
            assert result.status_code == 200
            assert mock_fetcher.fetch.call_count == 4
