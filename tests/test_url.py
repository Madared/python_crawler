import pytest

from crawler.url import is_same_domain, normalize_url, resolve_url


class TestNormalizeUrl:
    @pytest.mark.parametrize(
        ("input_url", "expected"),
        [
            ("https://Example.com/Path", "https://example.com/Path"),
            ("https://example.com/page#section", "https://example.com/page"),
            ("http://example.com:80/", "http://example.com/"),
            ("https://example.com:443/", "https://example.com/"),
            ("http://example.com:8080/", "http://example.com:8080/"),
            ("https://example.com", "https://example.com/"),
            ("https://example.com/?b=2&a=1", "https://example.com/?a=1&b=2"),
            ("https://example.com/a/../b", "https://example.com/b"),
            ("https://example.com/a/./b", "https://example.com/a/b"),
            ("https://example.com/%2f", "https://example.com/%2F"),
            ("https://example.com/%c3%a9", "https://example.com/%C3%A9"),
            ("https://example.com/about/", "https://example.com/about/"),
            ("http://[::1]/path", "http://[::1]/path"),
        ],
    )
    def test_normalize(self, input_url, expected):
        assert normalize_url(input_url) == expected


class TestResolveUrl:
    @pytest.mark.parametrize(
        ("href", "base_url", "expected"),
        [
            ("https://example.com/page", "https://other.com/", "https://example.com/page"),
            ("/about", "https://example.com", "https://example.com/about"),
            ("page.html", "https://example.com/dir/", "https://example.com/dir/page.html"),
            ("../parent", "https://example.com/a/b/", "https://example.com/a/parent"),
            ("javascript:void(0)", "https://example.com/", None),
            ("mailto:a@b.com", "https://example.com/", None),
            ("ftp://example.com", "https://example.com/", None),
            ("", "https://example.com/", None),
            ("  ", "https://example.com/", None),
            ("?query=1", "https://example.com/page", "https://example.com/page?query=1"),
            (
                "/path with spaces",
                "https://example.com",
                "https://example.com/path%20with%20spaces",
            ),
            ("/café", "https://example.com", "https://example.com/caf%C3%A9"),
        ],
    )
    def test_resolve(self, href, base_url, expected):
        assert resolve_url(href, base_url) == expected


class TestIsSameDomain:
    @pytest.mark.parametrize(
        ("url", "domain", "expected"),
        [
            ("http://example.com/page", "example.com", True),
            ("http://sub.example.com/page", "example.com", False),
            ("http://other.com/page", "example.com", False),
            ("HTTP://EXAMPLE.COM", "example.com", True),
            ("http://example.com:8080", "example.com", True),
            ("http://93.184.216.34/path", "93.184.216.34", True),
            ("not-a-url", "example.com", False),
        ],
    )
    def test_is_same_domain(self, url, domain, expected):
        assert is_same_domain(url, domain) == expected
