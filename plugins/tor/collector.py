"""Tor plugin'i — .onion adreslerini SOCKS5 proxy üzerinden toplar."""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class TorCollector(BaseCollector):
    id = "tor"
    name = "Tor (.onion)"
    network_type = "tor"

    def _session(self, cfg: dict[str, Any]) -> requests.Session:
        session = requests.Session()
        session.proxies = {
            "http": f"socks5h://{cfg.get('socks5_host', '127.0.0.1')}:{cfg.get('socks5_port', 9050)}",
            "https": f"socks5h://{cfg.get('socks5_host', '127.0.0.1')}:{cfg.get('socks5_port', 9050)}",
        }
        return session

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        url = cfg.get("url")
        if not url:
            return CollectionResult(items=[], success=False, error="url gerekli")

        try:
            resp = self._session(cfg).get(url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        items = [
            CollectedItem(
                url=url,
                title=soup.title.string.strip() if soup.title else None,
                raw_content=text,
                metadata={"network": "tor"},
            )
        ]
        return CollectionResult(items=items, metadata={"url": url, "network": "tor"})

    def health_check(self) -> bool:
        url = self.config.get("url")
        if not url:
            return False
        try:
            return self._session(self.config).get(url, timeout=30).status_code < 500
        except requests.RequestException:
            return False
