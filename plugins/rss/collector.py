"""RSS/Atom Feed plugin'i — feed okuyucu."""

from __future__ import annotations

from typing import Any

import feedparser
import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class RssCollector(BaseCollector):
    id = "rss"
    name = "RSS/Atom Feed"
    network_type = "rss"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        feed_url = cfg.get("feed_url")
        if not feed_url:
            return CollectionResult(items=[], success=False, error="feed_url gerekli")

        try:
            resp = requests.get(feed_url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        parsed = feedparser.parse(resp.content)
        if parsed.bozo and not parsed.entries:
            return CollectionResult(items=[], success=False, error="Geçersiz feed")

        max_items = cfg.get("max_items", 50)
        items = []
        for entry in parsed.entries[:max_items]:
            items.append(
                CollectedItem(
                    url=entry.get("link"),
                    title=entry.get("title"),
                    raw_content=entry.get("summary", "") or entry.get("description", ""),
                    published_at=entry.get("published"),
                    metadata={"feed": feed_url},
                )
            )
        return CollectionResult(items=items, metadata={"feed": feed_url})

    def health_check(self) -> bool:
        feed_url = self.config.get("feed_url")
        if not feed_url:
            return False
        try:
            return requests.head(feed_url, timeout=10).status_code < 500
        except requests.RequestException:
            return False
