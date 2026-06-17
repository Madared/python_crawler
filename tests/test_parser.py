import pytest

from crawler.parser import extract_links


class TestExtractLinks:
    @pytest.mark.parametrize(
        ("html", "base_url", "expected"),
        [
            # Absolute link
            (
                '<a href="https://example.com/page">',
                "https://example.com",
                ["https://example.com/page"],
            ),
            # Relative root link
            (
                '<a href="/about">',
                "https://example.com",
                ["https://example.com/about"],
            ),
            # Relative dir link
            (
                '<a href="page.html">',
                "https://example.com/dir/",
                ["https://example.com/dir/page.html"],
            ),
            # Base tag override
            (
                '<base href="https://other.com/"><a href="page.html">',
                "https://example.com",
                ["https://other.com/page.html"],
            ),
            # Fragment-only link
            (
                '<a href="#section">',
                "https://example.com",
                [],
            ),
            # javascript: link
            (
                '<a href="javascript:void(0)">',
                "https://example.com",
                [],
            ),
            # mailto: link
            (
                '<a href="mailto:a@b.com">',
                "https://example.com",
                [],
            ),
            # Duplicate links
            (
                '<a href="/a"><a href="/a">',
                "https://example.com",
                ["https://example.com/a"],
            ),
            # No links
            (
                "<p>no links here</p>",
                "https://example.com",
                [],
            ),
            # Empty href
            (
                '<a href="">',
                "https://example.com",
                [],
            ),
            # Whitespace-only href
            (
                '<a href="  ">',
                "https://example.com",
                [],
            ),
            # Query-only href
            (
                '<a href="?query=1">',
                "https://example.com/page",
                ["https://example.com/page?query=1"],
            ),
            # Special characters
            (
                '<a href="/path with spaces">',
                "https://example.com",
                ["https://example.com/path%20with%20spaces"],
            ),
            # Unicode in href
            (
                '<a href="/café">',
                "https://example.com",
                ["https://example.com/caf%C3%A9"],
            ),
            # Empty HTML
            (
                "",
                "https://example.com",
                [],
            ),
            # HTML with no body
            (
                "<html><head></head></html>",
                "https://example.com",
                [],
            ),
            # Multiple base tags - first wins
            (
                '<base href="/a/"><base href="/b/"><a href="page">',
                "https://example.com",
                ["https://example.com/a/page"],
            ),
            # Relative link with parent ref
            (
                '<a href="../page">',
                "https://example.com/a/b/",
                ["https://example.com/a/page"],
            ),
            # External link not filtered
            (
                '<a href="https://other.com/page">',
                "https://example.com",
                ["https://other.com/page"],
            ),
        ],
    )
    def test_extract_links(self, html, base_url, expected):
        assert extract_links(html, base_url) == expected
