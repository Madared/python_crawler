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
            assert "200 https://example.com/" in out
            assert "  -> https://example.com/page1" in out
            assert "  -> https://example.com/page2" in out
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

    async def test_crawl_redirect_cross_domain(self, capsys):
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
            captured = capsys.readouterr()

            assert result.status == CrawlStatus.SUCCESS
            assert "https://other.com/page" in captured.out

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
            assert captured.err == ""
