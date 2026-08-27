"""Web Scraper plugin'i — genel amaçlı web sayfası toplama."""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class WebScraperCollector(BaseCollector):
    id = "web-scraper"
    name = "Web Scraper"
    network_type = "www"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        url = cfg.get("url")
        if not url:
            return CollectionResult(items=[], success=False, error="url gerekli")

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        soup = BeautifulSoup(resp.text, "html.parser")
        selector = cfg.get("css_selector")
        if selector:
            nodes = soup.select(selector)
        else:
            nodes = [soup]

        items = []
        for node in nodes:
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            items.append(
                CollectedItem(
                    url=url,
                    title=soup.title.string.strip() if soup.title else None,
                    raw_content=text,
                    metadata={"depth": cfg.get("depth", 1)},
                )
            )
        return CollectionResult(items=items, metadata={"url": url})

    def health_check(self) -> bool:
        url = self.config.get("url")
        if not url:
            return False
        try:
            return requests.head(url, timeout=10).status_code < 500
        except requests.RequestException:
            return False
