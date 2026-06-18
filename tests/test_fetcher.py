import httpx
import pytest
import respx

from crawler.fetcher import Fetcher


@pytest.fixture
async def client():
    c = httpx.AsyncClient(follow_redirects=True, max_redirects=10)
    yield c
    await c.aclose()


@pytest.fixture
async def fetcher(client):
    return Fetcher(client=client)


class TestFetcher:
    @pytest.mark.parametrize(
        ("url", "status", "headers", "body", "expected_html", "expected_error"),
        [
            # 1. 200 with text/html
            (
                "https://example.com",
                200,
                {"content-type": "text/html"},
                "<html><body>Hello</body></html>",
                "<html><body>Hello</body></html>",
                None,
            ),
            # 2. 404
            (
                "https://example.com/not-found",
                404,
                {"content-type": "text/html"},
                "<html><body>Not Found</body></html>",
                "<html><body>Not Found</body></html>",
                None,
            ),
            # 8. Non-HTML content type
            (
                "https://example.com/doc.pdf",
                200,
                {"content-type": "application/pdf"},
                "%PDF-1.4...",
                None,
                None,
            ),
            # 9. HTML with charset
            (
                "https://example.com",
                200,
                {"content-type": "text/html; charset=utf-8"},
                "<html></html>",
                "<html></html>",
                None,
            ),
            # 400 Bad Request
            (
                "https://example.com/bad-request",
                400,
                {"content-type": "text/html"},
                "<html>Bad Request</html>",
                "<html>Bad Request</html>",
                None,
            ),
            # 500 Internal Server Error
            (
                "https://example.com/error",
                500,
                {"content-type": "text/html"},
                "<html>Server Error</html>",
                "<html>Server Error</html>",
                None,
            ),
            # 15. Empty body
            (
                "https://example.com",
                200,
                {"content-type": "text/html"},
                "",
                "",
                None,
            ),
        ],
    )
    async def test_fetch_success(
        self, fetcher, url, status, headers, body, expected_html, expected_error
    ):
        async with respx.mock:
            respx.get(url).respond(status, text=body, headers=headers)
            result = await fetcher.fetch(url)
            assert result.status_code == status
            assert result.html == expected_html
            assert result.error == expected_error
            assert result.final_url == url

    # 3. Redirect chain
    async def test_fetch_redirect_chain(self, fetcher):
        async with respx.mock:
            respx.get("https://example.com/start").respond(
                301, headers={"Location": "https://example.com/final"}
            )
            respx.get("https://example.com/final").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            result = await fetcher.fetch("https://example.com/start")
            assert result.status_code == 200
            assert result.html == "<html></html>"
            assert result.final_url == "https://example.com/final"
            assert result.error is None

    # 4. Cross-domain redirect
    async def test_fetch_cross_domain_redirect(self, fetcher):
        async with respx.mock:
            respx.get("https://example.com/redirect").respond(
                301, headers={"Location": "https://other.com/page"}
            )
            respx.get("https://other.com/page").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            result = await fetcher.fetch("https://example.com/redirect")
            assert result.status_code == 200
            assert result.html == "<html></html>"
            assert result.final_url == "https://other.com/page"

    # 5. Timeout
    async def test_fetch_timeout(self, fetcher):
        async with respx.mock:
            respx.get("https://example.com").mock(side_effect=httpx.ReadTimeout("Read timed out"))
            result = await fetcher.fetch("https://example.com")
            assert result.status_code == 0
            assert result.html is None
            assert result.error is not None
            assert "time" in result.error.lower()

    # 6. DNS failure
    async def test_fetch_dns_failure(self, fetcher):
        async with respx.mock:
            respx.get("https://invalid.example").mock(
                side_effect=httpx.ConnectError("DNS resolution failed")
            )
            result = await fetcher.fetch("https://invalid.example")
            assert result.status_code == 0
            assert result.html is None
            assert result.error is not None

    # 7. SSL error
    async def test_fetch_ssl_error(self, fetcher):
        async with respx.mock:
            respx.get("https://example.com").mock(
                side_effect=httpx.ConnectError("SSL certificate verification failed")
            )
            result = await fetcher.fetch("https://example.com")
            assert result.status_code == 0
            assert result.html is None
            assert result.error is not None

    # 10. Connection refused
    async def test_fetch_connection_refused(self, fetcher):
        async with respx.mock:
            respx.get("https://example.com:9999").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            result = await fetcher.fetch("https://example.com:9999")
            assert result.status_code == 0
            assert result.html is None
            assert result.error is not None

    # 11. Large response
    async def test_fetch_large_response(self, client):
        small_fetcher = Fetcher(client=client, max_response_size=1024)
        async with respx.mock:
            large_body = "x" * (2 * 1024)
            respx.get("https://example.com").respond(
                200, text=large_body, headers={"content-type": "text/html"}
            )
            result = await small_fetcher.fetch("https://example.com")
            assert result.status_code == 200
            assert result.html is not None
            assert len(result.html) <= 1024
            assert result.error is not None
            assert "truncated" in result.error.lower()

    # 13. User-Agent header
    async def test_user_agent_header(self):
        client = httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "TestCrawler/1.0"})
        fetcher = Fetcher(client=client)
        async with respx.mock:
            route = respx.get("https://example.com").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            await fetcher.fetch("https://example.com")
            request = route.calls.last.request
            assert request.headers["User-Agent"] == "TestCrawler/1.0"
        await client.aclose()

    # 14. Max redirects
    async def test_max_redirects(self, fetcher):
        async with respx.mock:
            respx.get("https://example.com").respond(
                301, headers={"Location": "https://example.com"}
            )
            result = await fetcher.fetch("https://example.com")
            assert result.status_code == 0
            assert result.html is None
            assert result.error is not None

    # 17. Invalid URL
    async def test_fetch_invalid_url(self, fetcher):
        result = await fetcher.fetch("not a valid url")
        assert result.status_code == 0
        assert result.html is None
        assert result.error is not None
