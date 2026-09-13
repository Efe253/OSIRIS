"""RSS/Atom Feed plugin'i — feed okuyucu."""

from __future__ import annotations

from typing import Any

import feedparser
import requests
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import fetch_url

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted)"}
_MAX_BYTES = 2_000_000


class RssCollector(BaseCollector):
    id = "rss"
    name = "RSS/Atom Feed"
    network_type = "rss"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        feed_url = cfg.get("feed_url")
        if not feed_url or not isinstance(feed_url, str):
            return CollectionResult(items=[], success=False, error="feed_url gerekli")
        try:
            resp = fetch_url(requests, "GET", feed_url, timeout=30, headers=_HEADERS,
                             verify=True, max_bytes=_MAX_BYTES)
            resp.raise_for_status()
        except (requests.RequestException, ValueError) as exc:
            return CollectionResult(items=[], success=False, error=str(exc)[:500])

        parsed = feedparser.parse(resp.content[:_MAX_BYTES])
        if parsed.bozo and not parsed.entries:
            return CollectionResult(items=[], success=False, error="Geçersiz feed")

        try:
            max_items = int(cfg.get("max_items", 50))
        except (TypeError, ValueError):
            max_items = 50
        max_items = max(1, min(max_items, 200))
        items = []
        for entry in parsed.entries[:max_items]:
            items.append(
                CollectedItem(
                    url=str(entry.get("link", ""))[:2048] or None,
                    title=str(entry.get("title", ""))[:500] or None,
                    raw_content=str(entry.get("summary", "") or entry.get("description", ""))[:50_000],
                    published_at=str(entry.get("published", ""))[:100] or None,
                    metadata={"feed": feed_url[:1000]},
                )
            )
        return CollectionResult(items=items, metadata={"feed": feed_url})

    def health_check(self) -> bool:
        feed_url = self.config.get("feed_url")
        if not feed_url or not isinstance(feed_url, str):
            return False
        try:
            return fetch_url(
                requests, "HEAD", feed_url, timeout=10, headers=_HEADERS,
                verify=True, max_bytes=0,
            ).status_code < 500
        except (requests.RequestException, ValueError):
            return False
