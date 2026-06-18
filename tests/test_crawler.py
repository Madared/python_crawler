import asyncio

import httpx
import respx

from crawler.crawler import CrawlStatus, run_crawl


class TestCrawler:
    async def test_crawl_basic(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/page1">link1</a><a href="/page2">link2</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/page1").respond(
                200, text='<a href="/page3">link3</a>', headers={"content-type": "text/html"}
            )
            respx.get("https://example.com/page2").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            respx.get("https://example.com/page3").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_max_pages(self):
        links = "".join(f'<a href="/page{i}">link{i}</a>' for i in range(10))
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text=links, headers={"content-type": "text/html"}
            )
            respx.get("https://example.com/page0").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", max_pages=2, concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_error_handling(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/ok">ok</a><a href="/bad">bad</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/ok").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            respx.get("https://example.com/bad").respond(
                500, text="<html>Error</html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.PARTIAL

    async def test_crawl_output_format(self, capsys):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/page1">link1</a><a href="/page2">link2</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/page1").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            respx.get("https://example.com/page2").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            captured = capsys.readouterr()

            assert result.status == CrawlStatus.SUCCESS
            out = captured.out
            assert "Crawl complete" in out
            assert "3 pages" in out
            err = captured.err
            assert err == ""

    async def test_crawl_domain_scoping(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text='<a href="https://other.com/page">external</a>',
                headers={"content-type": "text/html"},
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_redirect_same_domain(self):
        async with respx.mock:
            respx.get("https://example.com/start").respond(
                301, headers={"Location": "https://example.com/final"}
            )
            respx.get("https://example.com/final").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com/start", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_redirect_cross_domain(self):
        async with respx.mock:
            respx.get("https://example.com/start").respond(
                301, headers={"Location": "https://other.com/page"}
            )
            respx.get("https://other.com/page").respond(
                200,
                text='<a href="/another">link</a>',
                headers={"content-type": "text/html"},
            )

            result = await run_crawl("https://example.com/start", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS
            assert result.stats.visited == 1

    async def test_crawl_empty_site(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text="<html><body>no links</body></html>",
                headers={"content-type": "text/html"},
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_exit_code_zero(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_exit_code_one(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                500, text="Error", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.PARTIAL

    async def test_crawl_concurrent_limit(self):
        links = "".join(f'<a href="/page{i}">link{i}</a>' for i in range(9))
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text=links, headers={"content-type": "text/html"}
            )
            for i in range(9):
                respx.get(f"https://example.com/page{i}").respond(
                    200, text="<html></html>", headers={"content-type": "text/html"}
                )

            result = await run_crawl("https://example.com", concurrency=3)
            assert result.status == CrawlStatus.SUCCESS

    async def test_crawl_client_cleanup(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_concurrency_chain(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text='<a href="/p0">p0</a>', headers={"content-type": "text/html"}
            )
            for i in range(49):
                next_link = f'<a href="/p{i + 1}">p{i + 1}</a>' if i < 48 else ""
                respx.get(f"https://example.com/p{i}").respond(
                    200, text=next_link, headers={"content-type": "text/html"}
                )

            result = await run_crawl("https://example.com", concurrency=10)
            assert result.status == CrawlStatus.SUCCESS

    async def test_concurrency_diamond(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text="".join(f'<a href="/p{i}">p{i}</a>' for i in range(1, 6)),
                headers={"content-type": "text/html"},
            )
            for i in range(1, 6):
                respx.get(f"https://example.com/p{i}").respond(
                    200,
                    text="".join(f'<a href="/p{j}">p{j}</a>' for j in range(6, 11)),
                    headers={"content-type": "text/html"},
                )
            for i in range(6, 11):
                respx.get(f"https://example.com/p{i}").respond(
                    200,
                    text='<a href="/target">target</a>',
                    headers={"content-type": "text/html"},
                )
            respx.get("https://example.com/target").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=5)
            assert result.status == CrawlStatus.SUCCESS

    async def test_concurrency_redirect_chain(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/chain-start">start</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/chain-start").respond(
                301, headers={"Location": "https://example.com/mid"}
            )
            respx.get("https://example.com/mid").respond(
                301, headers={"Location": "https://example.com/end"}
            )
            respx.get("https://example.com/end").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=5)
            assert result.status == CrawlStatus.SUCCESS

    async def test_concurrency_max_pages_under_load(self):
        links = "".join(f'<a href="/p{i}">link{i}</a>' for i in range(99))
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text=links, headers={"content-type": "text/html"}
            )
            for i in range(4):
                respx.get(f"https://example.com/p{i}").respond(
                    200, text="<html></html>", headers={"content-type": "text/html"}
                )

            result = await run_crawl("https://example.com", max_pages=5, concurrency=10)
            assert result.status == CrawlStatus.SUCCESS

    async def test_concurrency_mixed_errors(self):
        links = "".join(f'<a href="/p{i}">link{i}</a>' for i in range(40))
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200, text=links, headers={"content-type": "text/html"}
            )
            for i in range(40):
                status = 200 if i % 2 == 0 else 500
                respx.get(f"https://example.com/p{i}").respond(
                    status, text="<html></html>", headers={"content-type": "text/html"}
                )

            result = await run_crawl("https://example.com", concurrency=8)
            assert result.status == CrawlStatus.PARTIAL

    async def test_concurrency_rapid_exhaustion(self):
        async with respx.mock:
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/child">link</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/child").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=20)
            assert result.status == CrawlStatus.SUCCESS

    async def test_robots_disallow_path(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(
                200,
                text="User-agent: *\nDisallow: /private/",
                headers={"content-type": "text/plain"},
            )
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/ok">ok</a><a href="/private/page">private</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/ok").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_robots_no_robots_txt(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(404)
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/page">page</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/page").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_robots_allow_overrides(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(
                200,
                text="User-agent: *\nDisallow: /\nAllow: /public/",
                headers={"content-type": "text/plain"},
            )
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/public/page">public</a><a href="/private/page">private</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/public/page").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_robots_disallowed_not_failure(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(
                200,
                text="User-agent: *\nDisallow: /blocked",
                headers={"content-type": "text/plain"},
            )
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/blocked">blocked</a>',
                headers={"content-type": "text/html"},
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS
            assert result.stats.visited == 2
            assert result.stats.failed == 0

    async def test_robots_all_allowed(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(
                200,
                text="User-agent: *\nAllow: /",
                headers={"content-type": "text/plain"},
            )
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/page">page</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/page").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_verbose_logging(self, capsys):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1, verbose=True)
            captured = capsys.readouterr()
            assert result.status == CrawlStatus.SUCCESS
            assert "visited" in captured.err
            assert "discovered" in captured.err
            assert "failed" in captured.err

    async def test_non_verbose(self, capsys):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1, verbose=False)
            captured = capsys.readouterr()
            assert result.status == CrawlStatus.SUCCESS
            assert "Crawl complete" in captured.out
            assert captured.err == ""

    async def test_max_time_completes(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1, max_time=5.0)
            assert result.status == CrawlStatus.SUCCESS

    async def test_max_time_triggers(self):
        async def slow_page(request):
            await asyncio.sleep(10)
            return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").mock(side_effect=slow_page)

            result = await run_crawl("https://example.com", concurrency=1, max_time=0.1)
            assert result.status == CrawlStatus.PARTIAL

    async def test_max_time_default(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_robots_txt_timeout_fallback(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").mock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_robots_txt_connection_error(self):
        async with respx.mock:
            respx.get("https://example.com/robots.txt").mock(
                side_effect=httpx.ConnectError("DNS failure")
            )
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1)
            assert result.status == CrawlStatus.SUCCESS

    async def test_invalid_seed_url_fatal(self):
        result = await run_crawl("not-a-valid-url", concurrency=1)
        assert result.status == CrawlStatus.FATAL
        assert result.stats.visited == 0

    async def test_unsupported_scheme_url(self):
        result = await run_crawl("ftp://example.com", concurrency=1)
        assert result.status == CrawlStatus.PARTIAL
        assert result.stats.visited == 1
        assert result.stats.failed == 1


class TestDummyStorage:
    async def test_save_called(self):
        from crawler.crawler import DummyStorage
        from crawler.fetcher import FetchResult

        storage = DummyStorage()
        result = FetchResult(
            status_code=200,
            html="<html></html>",
            final_url="https://example.com/",
            content_type="text/html",
            error=None,
        )
        await storage.save(result)

    async def test_close_does_not_raise(self):
        from crawler.crawler import DummyStorage

        storage = DummyStorage()
        await storage.close()

    async def test_custom_storage(self):
        from crawler.crawler import Storage, run_crawl
        from crawler.fetcher import FetchResult

        class TestStorage(Storage):
            def __init__(self):
                self.saved: list[FetchResult] = []

            async def save(self, result: FetchResult) -> None:
                self.saved.append(result)

            async def close(self) -> None:
                self.saved.append(None)

        storage = TestStorage()
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1, storage=storage)
            assert result.status == CrawlStatus.SUCCESS
            assert len(storage.saved) == 2
            assert storage.saved[0] is not None
            assert storage.saved[1] is None

    async def test_storage_save_called_once_per_page(self):
        from crawler.crawler import Storage, run_crawl
        from crawler.fetcher import FetchResult

        class CallbackStorage(Storage):
            def __init__(self):
                self.count = 0

            async def save(self, result: FetchResult) -> None:
                self.count += 1

        storage = CallbackStorage()
        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").respond(
                200,
                text='<a href="/a">a</a><a href="/b">b</a>',
                headers={"content-type": "text/html"},
            )
            respx.get("https://example.com/a").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )
            respx.get("https://example.com/b").respond(
                200, text="<html></html>", headers={"content-type": "text/html"}
            )

            result = await run_crawl("https://example.com", concurrency=1, storage=storage)
            assert result.status == CrawlStatus.SUCCESS
            assert storage.count == 3


class TestWorkerPool:
    async def test_worker_crash_handled(self, capsys):
        from unittest.mock import AsyncMock

        import httpx
        import pytest

        from crawler.crawler import CrawlerOptions
        from crawler.crawler._context import CrawlerContext
        from crawler.crawler._dispatcher import WorkDispatcher
        from crawler.crawler._pool import WorkerPool
        from crawler.fetcher import RetryFetcher, SimpleFetcher
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        frontier = Frontier("https://example.com", "example.com")
        client = httpx.AsyncClient()
        inner = SimpleFetcher(client=client)
        fetcher = RetryFetcher(inner, max_retries=0)
        options = CrawlerOptions(concurrency=1, verbose=False)

        shutdown_event = AsyncMock(spec=asyncio.Event)
        shutdown_event.is_set.return_value = False

        ctx = CrawlerContext(
            domain="example.com",
            frontier=frontier,
            client=client,
            fetcher=fetcher,
            shutdown_event=shutdown_event,
            output_lock=asyncio.Lock(),
            robots_rules=RobotsTxtRules(),
            effective_delay=0.0,
            options=options,
            signal_handler_registered=False,
        )

        dispatch = AsyncMock(spec=WorkDispatcher)
        dispatch.work.side_effect = RuntimeError("Worker crashed!")

        pool = WorkerPool(ctx, dispatch)
        with pytest.raises(RuntimeError, match="Worker crashed!"):
            await pool.run()

    async def test_worker_timeout_produces_partial(self):
        import httpx
        import respx

        from crawler.crawler import run_crawl

        async def slow_page(request):
            await asyncio.sleep(10)
            return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

        async with respx.mock:
            respx.get("https://example.com/robots.txt").respond(200, text="")
            respx.get("https://example.com/").mock(side_effect=slow_page)

            result = await run_crawl("https://example.com", concurrency=1, max_time=0.1)
            assert result.status == CrawlStatus.PARTIAL


class TestCrawlerContext:
    async def test_close_cleans_up_client(self):
        import httpx

        from crawler.crawler import CrawlerOptions
        from crawler.crawler._context import CrawlerContext
        from crawler.fetcher import RetryFetcher, SimpleFetcher
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        client = httpx.AsyncClient()
        inner = SimpleFetcher(client=client)
        fetcher = RetryFetcher(inner, max_retries=0)
        frontier = Frontier("https://example.com", "example.com")

        ctx = CrawlerContext(
            domain="example.com",
            frontier=frontier,
            client=client,
            fetcher=fetcher,
            shutdown_event=asyncio.Event(),
            output_lock=asyncio.Lock(),
            robots_rules=RobotsTxtRules(),
            effective_delay=0.2,
            options=CrawlerOptions(),
            signal_handler_registered=False,
        )

        assert not client.is_closed
        await ctx.close()
        assert client.is_closed

    async def test_close_idempotent(self):
        import httpx

        from crawler.crawler import CrawlerOptions
        from crawler.crawler._context import CrawlerContext
        from crawler.fetcher import RetryFetcher, SimpleFetcher
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        client = httpx.AsyncClient()
        inner = SimpleFetcher(client=client)
        fetcher = RetryFetcher(inner, max_retries=0)
        frontier = Frontier("https://example.com", "example.com")

        ctx = CrawlerContext(
            domain="example.com",
            frontier=frontier,
            client=client,
            fetcher=fetcher,
            shutdown_event=asyncio.Event(),
            output_lock=asyncio.Lock(),
            robots_rules=RobotsTxtRules(),
            effective_delay=0.2,
            options=CrawlerOptions(),
            signal_handler_registered=False,
        )

        await ctx.close()
        await ctx.close()
        assert client.is_closed

    async def test_close_with_signal_handler_registered(self):
        import signal

        import httpx

        from crawler.crawler import CrawlerOptions
        from crawler.crawler._context import CrawlerContext
        from crawler.fetcher import RetryFetcher, SimpleFetcher
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        client = httpx.AsyncClient()
        inner = SimpleFetcher(client=client)
        fetcher = RetryFetcher(inner, max_retries=0)
        frontier = Frontier("https://example.com", "example.com")

        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()
        loop.add_signal_handler(signal.SIGINT, shutdown_event.set)

        ctx = CrawlerContext(
            domain="example.com",
            frontier=frontier,
            client=client,
            fetcher=fetcher,
            shutdown_event=shutdown_event,
            output_lock=asyncio.Lock(),
            robots_rules=RobotsTxtRules(),
            effective_delay=0.2,
            options=CrawlerOptions(),
            signal_handler_registered=True,
        )

        await ctx.close()
        assert client.is_closed

        loop.remove_signal_handler(signal.SIGINT)

    async def test_close_no_loop_still_cleans_up(self):
        import httpx

        from crawler.crawler import CrawlerOptions
        from crawler.crawler._context import CrawlerContext
        from crawler.fetcher import RetryFetcher, SimpleFetcher
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        client = httpx.AsyncClient()
        inner = SimpleFetcher(client=client)
        fetcher = RetryFetcher(inner, max_retries=0)
        frontier = Frontier("https://example.com", "example.com")

        ctx = CrawlerContext(
            domain="example.com",
            frontier=frontier,
            client=client,
            fetcher=fetcher,
            shutdown_event=asyncio.Event(),
            output_lock=asyncio.Lock(),
            robots_rules=RobotsTxtRules(),
            effective_delay=0.2,
            options=CrawlerOptions(),
            signal_handler_registered=False,
        )

        await ctx.close()
        assert client.is_closed


class TestWorkDispatcher:
    async def test_skip_disallowed_by_robots(self):
        from unittest.mock import AsyncMock

        from crawler.crawler._dispatcher import WorkDispatcher
        from crawler.crawler._logger import CrawlLogger
        from crawler.crawler._types import DispatcherAsync, DispatcherConfig, DispatcherDeps
        from crawler.frontier import Frontier
        from crawler.robotstxt import parse_robots_txt

        frontier = Frontier("https://example.com/private/page", "example.com")
        url = await frontier.next_url()
        assert url is not None

        rules = parse_robots_txt("User-agent: *\nDisallow: /private/")
        deps = DispatcherDeps(
            frontier=frontier,
            fetcher=AsyncMock(),
            logger=CrawlLogger(verbose=False),
            storage=AsyncMock(),
        )
        config = DispatcherConfig(delay=0.0, robots_rules=rules)
        async_ctx = DispatcherAsync(output_lock=asyncio.Lock(), shutdown_event=asyncio.Event())

        dispatch = WorkDispatcher(deps, config, async_ctx)
        await dispatch.work(url)

        assert frontier.stats.visited == 1
        assert frontier.stats.failed == 0
        deps.fetcher.fetch.assert_not_called()

    async def test_fetch_links_and_store(self):
        from unittest.mock import AsyncMock, patch

        from crawler.crawler._dispatcher import WorkDispatcher
        from crawler.crawler._logger import CrawlLogger
        from crawler.crawler._types import DispatcherAsync, DispatcherConfig, DispatcherDeps
        from crawler.fetcher import FetchResult
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        frontier = Frontier("https://example.com/", "example.com")
        url = await frontier.next_url()
        assert url is not None

        fetch_result = FetchResult(
            status_code=200,
            html='<a href="/page1">link</a>',
            final_url="https://example.com/",
            content_type="text/html",
            error=None,
        )
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch.return_value = fetch_result

        mock_storage = AsyncMock()

        deps = DispatcherDeps(
            frontier=frontier,
            fetcher=mock_fetcher,
            logger=CrawlLogger(verbose=False),
            storage=mock_storage,
        )
        config = DispatcherConfig(delay=0.0, robots_rules=RobotsTxtRules())
        async_ctx = DispatcherAsync(output_lock=asyncio.Lock(), shutdown_event=asyncio.Event())

        dispatch = WorkDispatcher(deps, config, async_ctx)
        with patch(
            "crawler.crawler._dispatcher.extract_links", return_value=["https://example.com/page1"]
        ):
            await dispatch.work(url)

        assert frontier.stats.visited == 1
        assert frontier.stats.failed == 0
        assert frontier.stats.discovered == 2
        mock_storage.save.assert_awaited_once_with(fetch_result)

    async def test_fetch_error_marks_failed(self):
        from unittest.mock import AsyncMock

        from crawler.crawler._dispatcher import WorkDispatcher
        from crawler.crawler._logger import CrawlLogger
        from crawler.crawler._types import DispatcherAsync, DispatcherConfig, DispatcherDeps
        from crawler.fetcher import FetchResult
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        frontier = Frontier("https://example.com/", "example.com")
        url = await frontier.next_url()
        assert url is not None

        fetch_result = FetchResult(
            status_code=0,
            html=None,
            final_url="https://example.com/",
            content_type="",
            error="Connection refused",
        )
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch.return_value = fetch_result

        deps = DispatcherDeps(
            frontier=frontier,
            fetcher=mock_fetcher,
            logger=CrawlLogger(verbose=False),
            storage=AsyncMock(),
        )
        config = DispatcherConfig(delay=0.0, robots_rules=RobotsTxtRules())
        async_ctx = DispatcherAsync(output_lock=asyncio.Lock(), shutdown_event=asyncio.Event())

        dispatch = WorkDispatcher(deps, config, async_ctx)
        await dispatch.work(url)

        assert frontier.stats.visited == 1
        assert frontier.stats.failed == 1

    async def test_delay_applied_after_success(self):
        from unittest.mock import AsyncMock, patch

        from crawler.crawler._dispatcher import WorkDispatcher
        from crawler.crawler._logger import CrawlLogger
        from crawler.crawler._types import DispatcherAsync, DispatcherConfig, DispatcherDeps
        from crawler.fetcher import FetchResult
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        frontier = Frontier("https://example.com/", "example.com")
        url = await frontier.next_url()
        assert url is not None

        fetch_result = FetchResult(
            status_code=200,
            html="<html></html>",
            final_url="https://example.com/",
            content_type="text/html",
            error=None,
        )
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch.return_value = fetch_result

        deps = DispatcherDeps(
            frontier=frontier,
            fetcher=mock_fetcher,
            logger=CrawlLogger(verbose=False),
            storage=AsyncMock(),
        )
        config = DispatcherConfig(delay=1.0, robots_rules=RobotsTxtRules())
        async_ctx = DispatcherAsync(output_lock=asyncio.Lock(), shutdown_event=asyncio.Event())

        dispatch = WorkDispatcher(deps, config, async_ctx)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await dispatch.work(url)

        mock_sleep.assert_awaited_once_with(1.0)

    async def test_no_delay_on_fetch_error(self):
        from unittest.mock import AsyncMock, patch

        from crawler.crawler._dispatcher import WorkDispatcher
        from crawler.crawler._logger import CrawlLogger
        from crawler.crawler._types import DispatcherAsync, DispatcherConfig, DispatcherDeps
        from crawler.fetcher import FetchResult
        from crawler.frontier import Frontier
        from crawler.robotstxt import RobotsTxtRules

        frontier = Frontier("https://example.com/", "example.com")
        url = await frontier.next_url()
        assert url is not None

        fetch_result = FetchResult(
            status_code=500,
            html=None,
            final_url="https://example.com/",
            content_type="text/html",
            error="Server error",
        )
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch.return_value = fetch_result

        deps = DispatcherDeps(
            frontier=frontier,
            fetcher=mock_fetcher,
            logger=CrawlLogger(verbose=False),
            storage=AsyncMock(),
        )
        config = DispatcherConfig(delay=1.0, robots_rules=RobotsTxtRules())
        async_ctx = DispatcherAsync(output_lock=asyncio.Lock(), shutdown_event=asyncio.Event())

        dispatch = WorkDispatcher(deps, config, async_ctx)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await dispatch.work(url)

        mock_sleep.assert_not_called()
