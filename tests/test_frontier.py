import asyncio

from crawler.frontier import Frontier


class TestFrontier:
    async def test_add_and_next(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        assert url == "https://example.com/"

        assert f.add_url("https://example.com/page1") is True
        assert f.stats.discovered == 2

        f.mark_done(url)
        assert f.stats.visited == 1
        assert not f.exhausted.is_set()

        url2 = await f.next_url()
        assert url2 == "https://example.com/page1"

        f.mark_done(url2)
        assert f.stats.visited == 2
        assert f.exhausted.is_set()

        assert await f.next_url() is None

    async def test_dedup(self):
        f = Frontier("https://example.com", "example.com")
        await f.next_url()

        assert f.add_url("https://example.com/page") is True
        assert f.add_url("https://example.com/page") is False
        assert f.stats.discovered == 2

    async def test_domain_filtering(self):
        f = Frontier("https://example.com", "example.com")
        assert f.add_url("https://other.com/page") is False
        assert f.stats.discovered == 1

    async def test_subdomain_filtering(self):
        f = Frontier("https://example.com", "example.com")
        assert f.add_url("https://sub.example.com/page") is False
        assert f.stats.discovered == 1

    async def test_max_pages(self):
        f = Frontier("https://example.com", "example.com", max_pages=2)
        await f.next_url()

        assert f.add_url("https://example.com/page1") is True
        assert f.stats.discovered == 2
        assert f.add_url("https://example.com/page2") is False
        assert f.stats.discovered == 2

    async def test_concurrent_add(self):
        f = Frontier("https://example.com", "example.com")
        await f.next_url()

        results = [f.add_url(f"https://example.com/page{i}") for i in range(10)]
        assert all(results)
        assert f.stats.discovered == 11

    async def test_concurrent_consume(self):
        f = Frontier("https://example.com", "example.com")
        urls_to_add = [f"https://example.com/page{i}" for i in range(5)]
        for url in urls_to_add:
            f._queued.add(url)
            f._queue.put_nowait(url)
            f._stats.discovered += 1

        consumed = set()

        async def consume():
            url = await f.next_url()
            if url:
                consumed.add(url)
                f.mark_done(url)
                return True
            return False

        results = await asyncio.gather(*[consume() for _ in range(6)])
        successes = [r for r in results if r]
        assert len(successes) == 6
        assert len(consumed) == 6

    async def test_exhaustion_with_active_workers(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        assert not f.exhausted.is_set()
        f.mark_done(url)
        assert f.exhausted.is_set()

    async def test_exhaustion_when_all_done(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        assert f.add_url("https://example.com/page") is True
        f.mark_done(url)
        assert not f.exhausted.is_set()

        url2 = await f.next_url()
        f.mark_done(url2)
        assert f.exhausted.is_set()

    async def test_mark_done_moves_to_visited(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        assert url is not None

        f.mark_done(url)

        assert f.add_url(url) is False

    async def test_visited_url_not_requeued(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        f.mark_done(url)

        assert f.add_url(url) is False

    async def test_in_progress_url_not_requeued(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()

        assert f.add_url(url) is False

    async def test_mark_done_idempotent(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()

        f.mark_done(url)
        assert f.stats.visited == 1

        f.mark_done(url)
        assert f.stats.visited == 1
        assert f._active_workers == 0

    async def test_exhaustion_cleared_by_new_url(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        f.mark_done(url)
        assert f.exhausted.is_set()

        assert f.add_url("https://example.com/new-page") is True
        assert not f.exhausted.is_set()

        url2 = await f.next_url()
        assert url2 == "https://example.com/new-page"

    async def test_concurrent_mark_done_no_race(self):
        f = Frontier("https://example.com", "example.com")
        assert f.add_url("https://example.com/page") is True

        async def work():
            url = await f.next_url()
            f.mark_done(url)

        await asyncio.gather(work(), work())
        assert f.exhausted.is_set()
        assert f.stats.visited == 2

    async def test_next_url_returns_none_on_empty(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        f.mark_done(url)
        result = await f.next_url()
        assert result is None

    async def test_seed_auto_added(self):
        f = Frontier("https://example.com/seed", "example.com")
        url = await f.next_url()
        assert url == "https://example.com/seed"
        assert f.stats.discovered == 1

    async def test_stats(self):
        f = Frontier("https://example.com", "example.com")
        url = await f.next_url()
        f.mark_done(url, success=False)
        assert f.stats.visited == 1
        assert f.stats.failed == 1

        assert f.add_url("https://example.com/page") is True
        url2 = await f.next_url()
        f.mark_done(url2, success=True)
        assert f.stats.visited == 2
        assert f.stats.failed == 1

    async def test_invalid_url_skipped(self):
        f = Frontier("https://example.com", "example.com")
        assert f.add_url("not-a-url") is False
        assert f.stats.discovered == 1
