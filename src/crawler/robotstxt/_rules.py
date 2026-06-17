from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class _Rule:
    kind: str
    pattern: str
    regex: re.Pattern


@dataclass
class RobotsTxtRules:
    _rules: list[_Rule] = field(default_factory=list)
    _crawl_delay: float | None = None

    def __post_init__(self) -> None:
        self._rules.sort(key=lambda r: len(r.pattern), reverse=True)

    def is_allowed(self, url_path: str) -> bool:
        for rule in self._rules:
            if rule.regex.search(url_path):
                return rule.kind == "allow"
        return True

    def get_crawl_delay(self, default: float = 0.0) -> float:
        if self._crawl_delay is not None:
            return max(self._crawl_delay, default)
        return default
