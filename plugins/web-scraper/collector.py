"""Web Scraper plugin'i — genel amaçlı web sayfası toplama."""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import fetch_url, safe_title

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted; contact: admin@localhost)"}
_MAX_BYTES = 2_000_000


class WebScraperCollector(BaseCollector):
    id = "web-scraper"
    name = "Web Scraper"
    network_type = "www"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        url = cfg.get("url")
        if not url or not isinstance(url, str):
            return CollectionResult(items=[], success=False, error="url gerekli")
        try:
            resp = fetch_url(requests, "GET", url, timeout=30, headers=_HEADERS,
                             verify=True, max_bytes=_MAX_BYTES)
            resp.raise_for_status()
        except (requests.RequestException, ValueError) as exc:
            return CollectionResult(items=[], success=False, error=str(exc)[:500])

        text = resp.text[:_MAX_BYTES]
        soup = BeautifulSoup(text, "html.parser")
        selector = cfg.get("css_selector")
        try:
            nodes = soup.select(selector)[:20] if selector else [soup]
        except Exception:  # noqa: BLE001
            nodes = [soup]

        title = safe_title(soup)
        items = []
        for node in nodes:
            node_text = node.get_text(" ", strip=True)[:50_000]
            if not node_text:
                continue
            items.append(
                CollectedItem(
                    url=url[:2048],
                    title=title,
                    raw_content=node_text,
                    metadata={"depth": cfg.get("depth", 1)},
                )
            )
            if len(items) >= 20:
                break
        return CollectionResult(items=items, metadata={"url": url})

    def health_check(self) -> bool:
        url = self.config.get("url")
        if not url or not isinstance(url, str):
            return False
        try:
            return fetch_url(
                requests, "HEAD", url, timeout=10, headers=_HEADERS,
                verify=True, max_bytes=0,
            ).status_code < 500
        except (requests.RequestException, ValueError):
            return False
