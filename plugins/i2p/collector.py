"""I2P plugin'i — eepsite'ları I2P HTTP proxy üzerinden toplar."""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class I2PCollector(BaseCollector):
    id = "i2p"
    name = "I2P (eepsite)"
    network_type = "i2p"

    def _session(self, cfg: dict[str, Any]) -> requests.Session:
        session = requests.Session()
        proxy = f"http://{cfg.get('http_proxy_host', '127.0.0.1')}:{cfg.get('http_proxy_port', 4444)}"
        session.proxies = {"http": proxy, "https": proxy}
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
        items = [
            CollectedItem(
                url=url,
                title=soup.title.string.strip() if soup.title else None,
                raw_content=soup.get_text(" ", strip=True),
                metadata={"network": "i2p"},
            )
        ]
        return CollectionResult(items=items, metadata={"url": url, "network": "i2p"})

    def health_check(self) -> bool:
        url = self.config.get("url")
        if not url:
            return False
        try:
            return self._session(self.config).get(url, timeout=30).status_code < 500
        except requests.RequestException:
            return False
