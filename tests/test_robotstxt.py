import pytest

from crawler.robotstxt import parse_robots_txt


class TestParseRobotsTxt:
    @pytest.mark.parametrize(
        ("content", "user_agent", "path", "expected"),
        [
            # 1. Disallow path
            (
                "User-agent: *\nDisallow: /private/",
                "*",
                "/private/page",
                False,
            ),
            (
                "User-agent: *\nDisallow: /private/",
                "*",
                "/public/page",
                True,
            ),
            # 2. Allow overrides disallow
            (
                "User-agent: *\nDisallow: /private/\nAllow: /private/public.html",
                "*",
                "/private/public.html",
                True,
            ),
            (
                "User-agent: *\nDisallow: /private/\nAllow: /private/public.html",
                "*",
                "/private/other",
                False,
            ),
            # 3. Crawl-Delay (tested via separate test)
            # 4. UA-specific group
            (
                "User-agent: Googlebot\nDisallow: /bot-only/\nUser-agent: *\nAllow: /",
                "Googlebot",
                "/bot-only/page",
                False,
            ),
            # 5. UA wildcard fallback
            (
                "User-agent: Googlebot\nDisallow: /bot-only/\nUser-agent: *\nDisallow: /temp/",
                "MyBot",
                "/temp/page",
                False,
            ),
            (
                "User-agent: Googlebot\nDisallow: /bot-only/\nUser-agent: *\nAllow: /",
                "MyBot",
                "/bot-only/page",
                True,
            ),
            # 6. Longest match wins
            (
                "User-agent: *\nDisallow: /\nAllow: /public/",
                "*",
                "/public/page",
                True,
            ),
            (
                "User-agent: *\nDisallow: /\nAllow: /public/",
                "*",
                "/admin/page",
                False,
            ),
            # 7. Wildcard * in pattern
            (
                "User-agent: *\nDisallow: /*.pdf$",
                "*",
                "/doc.pdf",
                False,
            ),
            (
                "User-agent: *\nDisallow: /*.pdf$",
                "*",
                "/doc.pdf/more",
                True,
            ),
            # 8. Dollar anchor
            (
                "User-agent: *\nDisallow: /exact$",
                "*",
                "/exact",
                False,
            ),
            (
                "User-agent: *\nDisallow: /exact$",
                "*",
                "/exact/more",
                True,
            ),
            # 9. No robots.txt
            (
                "",
                "*",
                "/anything",
                True,
            ),
            # 10. Comments only
            (
                "# just a comment\n# another comment",
                "*",
                "/page",
                True,
            ),
            # 11. Comments stripped
            (
                "User-agent: *\nDisallow: /p # this is a comment",
                "*",
                "/p",
                False,
            ),
            # 12. Case-insensitive directives
            (
                "user-agent: *\ndisallow: /private/",
                "*",
                "/private/page",
                False,
            ),
            # 13. No matching rule
            (
                "User-agent: *\nDisallow: /admin/",
                "*",
                "/public/page",
                True,
            ),
            # 14. Allow all
            (
                "User-agent: *\nAllow: /",
                "*",
                "/anything/really/deep",
                True,
            ),
            # 15. Disallow all
            (
                "User-agent: *\nDisallow: /",
                "*",
                "/anything",
                False,
            ),
            # 16. Case-insensitive UA matching (regression)
            (
                "User-agent: GoogleBot\nDisallow: /",
                "googlebot",
                "/page",
                False,
            ),
            # 17. No fallback group (no * group)
            (
                "User-agent: Googlebot\nDisallow: /",
                "Bingbot",
                "/page",
                True,
            ),
            # 18. No User-agent lines at all
            (
                "Disallow: /",
                "*",
                "/page",
                True,
            ),
            # 19. Directive before any User-agent line
            (
                "Disallow: /private/\nUser-agent: *\nAllow: /",
                "*",
                "/private/page",
                True,
            ),
            # 20. Empty path
            (
                "User-agent: *\nAllow: /",
                "*",
                "",
                True,
            ),
            # 21. Wildcard before exact UA — exact still wins
            (
                "User-agent: *\nDisallow: /temp/\nUser-agent: Googlebot\nDisallow: /private/",
                "Googlebot",
                "/temp/page",
                True,
            ),
            (
                "User-agent: *\nDisallow: /temp/\nUser-agent: Googlebot\nDisallow: /private/",
                "Googlebot",
                "/private/page",
                False,
            ),
            # 22. Same path — specific UA overrides wildcard
            (
                "User-agent: *\nAllow: /page\nUser-agent: Googlebot\nDisallow: /page",
                "Googlebot",
                "/page",
                False,
            ),
            (
                "User-agent: *\nDisallow: /page\nUser-agent: Googlebot\nAllow: /page",
                "Googlebot",
                "/page",
                True,
            ),
        ],
    )
    def test_is_allowed(self, content, user_agent, path, expected):
        rules = parse_robots_txt(content, user_agent)
        assert rules.is_allowed(path) == expected

    @pytest.mark.parametrize(
        ("content", "user_agent", "default", "expected"),
        [
            # 3. Crawl-Delay
            (
                "User-agent: *\nCrawl-Delay: 5",
                "*",
                1.0,
                5.0,
            ),
            # Crawl-Delay with smaller default
            (
                "User-agent: *\nCrawl-Delay: 2",
                "*",
                3.0,
                3.0,
            ),
            # No Crawl-Delay
            (
                "User-agent: *\nDisallow: /",
                "*",
                0.2,
                0.2,
            ),
            # No Crawl-Delay, no default
            (
                "User-agent: *\nDisallow: /",
                "*",
                0.0,
                0.0,
            ),
            # Invalid Crawl-Delay value
            (
                "User-agent: *\nCrawl-Delay: abc",
                "*",
                1.0,
                1.0,
            ),
            # Multiple Crawl-Delays — first kept
            (
                "User-agent: *\nCrawl-Delay: 2\nCrawl-Delay: 5",
                "*",
                1.0,
                2.0,
            ),
            # No robots.txt
            (
                "",
                "*",
                0.5,
                0.5,
            ),
            # Decimal Crawl-Delay
            (
                "User-agent: *\nCrawl-Delay: 2.5",
                "*",
                0.0,
                2.5,
            ),
            # Zero Crawl-Delay — CLI default still applies
            (
                "User-agent: *\nCrawl-Delay: 0",
                "*",
                1.0,
                1.0,
            ),
        ],
    )
    def test_get_crawl_delay(self, content, user_agent, default, expected):
        rules = parse_robots_txt(content, user_agent)
        assert rules.get_crawl_delay(default) == expected
