from bs4 import BeautifulSoup

from crawler.url import resolve_url


def extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")

    base_tag = soup.find("base", href=True)
    if base_tag:
        resolved_base = resolve_url(base_tag["href"], base_url)
        if resolved_base:
            base_url = resolved_base

    seen = set()
    result = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith("#"):
            continue
        resolved = resolve_url(href, base_url)
        if resolved is None or resolved in seen:
            continue
        seen.add(resolved)
        result.append(resolved)
    return result
