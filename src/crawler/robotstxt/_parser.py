from __future__ import annotations

import re

from crawler.robotstxt._rules import RobotsTxtRules, _Rule


def _pattern_to_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    if anchored:
        pattern = pattern[:-1]
    regex = re.escape(pattern).replace(r"\*", ".*")
    if anchored:
        return re.compile(f"^{regex}$")
    return re.compile(f"^{regex}")


def _clean_line(line: str) -> str | None:
    stripped = line.split("#", 1)[0].strip()
    return stripped if stripped else None


def _find_group(cleaned_lines: list[str], user_agent: str) -> list[str] | None:
    exact_directives = None
    wildcard_directives = None
    current_collector = None

    for line in cleaned_lines:
        if not line.lower().startswith("user-agent:"):
            if current_collector is not None:
                current_collector.append(line)
            continue

        ua = line[len("user-agent:"):].strip()
        if ua.lower() == user_agent.lower():
            exact_directives = []
            current_collector = exact_directives
        elif ua == "*" and exact_directives is None and wildcard_directives is None:
            wildcard_directives = []
            current_collector = wildcard_directives
        else:
            current_collector = None

    return exact_directives if exact_directives is not None else wildcard_directives


def _parse_group(directives: list[str]) -> RobotsTxtRules:
    rules: list[_Rule] = []
    crawl_delay: float | None = None
    for line in directives:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key in ("disallow", "allow") and value:
            rules.append(_Rule(key, value, _pattern_to_regex(value)))
        elif key == "crawl-delay" and crawl_delay is None:
            try:
                crawl_delay = float(value)
            except ValueError:
                pass
    return RobotsTxtRules(rules, crawl_delay)


def parse_robots_txt(content: str, user_agent: str = "*") -> RobotsTxtRules:
    cleaned = [cl for line in content.splitlines() if (cl := _clean_line(line)) is not None]
    directives = _find_group(cleaned, user_agent)
    if directives is None:
        return RobotsTxtRules()
    return _parse_group(directives)
