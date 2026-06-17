import re
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse, urlunparse


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    port = parsed.port
    default_port = {"http": 80, "https": 443}.get(scheme)
    if port and port == default_port:
        port = None
    if port:
        netloc = f"[{hostname}]:{port}" if ":" in hostname else f"{hostname}:{port}"
    else:
        netloc = f"[{hostname}]" if ":" in hostname else hostname

    path = parsed.path or "/"
    ends_with_slash = path.endswith("/")

    segments = path.split("/")
    result = []
    for seg in segments:
        if seg == "..":
            if result:
                result.pop()
        elif seg and seg != ".":
            result.append(seg)
    path = "/" + "/".join(result) if result else "/"
    if ends_with_slash and not path.endswith("/"):
        path += "/"

    path = quote(path, safe="/%")
    path = re.sub(r"%[0-9a-f]{2}", lambda m: m.group(0).upper(), path)

    query = parsed.query
    if query:
        params = parse_qs(query, keep_blank_values=True)
        sorted_query = urlencode(sorted(params.items()), doseq=True)
    else:
        sorted_query = ""

    return urlunparse((scheme, netloc, path, parsed.params, sorted_query, ""))


def resolve_url(href: str, base_url: str) -> str | None:
    if not href or href.strip() == "":
        return None
    href = href.strip()
    scheme = urlparse(href).scheme
    if scheme and scheme not in ("http", "https"):
        return None
    resolved = urljoin(base_url, href)
    return normalize_url(resolved)


def is_same_domain(url: str, domain: str) -> bool:
    host = urlparse(url).hostname
    if host is None:
        return False
    return host.lower() == domain.lower().strip()
