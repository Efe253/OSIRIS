"""I2P plugin'i — eepsite'ları I2P HTTP proxy üzerinden toplar."""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import safe_title

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted)"}
_MAX_BYTES = 2_000_000


class I2PCollector(BaseCollector):
    id = "i2p"
    name = "I2P (eepsite)"
    network_type = "i2p"

    def _session(self, cfg: dict[str, Any]) -> requests.Session:
        session = requests.Session()
        host = str(cfg.get("http_proxy_host", "127.0.0.1"))
        try:
            port = int(cfg.get("http_proxy_port", 4444))
        except (TypeError, ValueError) as exc:
            raise ValueError("Geçersiz I2P proxy portu") from exc
        if host not in ("127.0.0.1", "::1"):
            raise ValueError("I2P proxy host yalnızca localhost olabilir")
        if not 1 <= port <= 65535:
            raise ValueError("Geçersiz I2P proxy portu")
        proxy = f"http://{host}:{port}"
        session.proxies = {"http": proxy, "https": proxy}
        session.headers.update(_HEADERS)
        return session

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        url = cfg.get("url")
        if not url or not isinstance(url, str):
            return CollectionResult(items=[], success=False, error="url gerekli")

        try:
            session = self._session(cfg)
        except ValueError as exc:
            return CollectionResult(items=[], success=False, error=str(exc))
        try:
            resp = session.get(url, timeout=60, verify=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc)[:500])

        soup = BeautifulSoup(resp.text[:_MAX_BYTES], "html.parser")
        items = [
            CollectedItem(
                url=url[:2048],
                title=safe_title(soup),
                raw_content=soup.get_text(" ", strip=True)[:50_000],
                metadata={"network": "i2p"},
            )
        ]
        return CollectionResult(items=items, metadata={"url": url, "network": "i2p"})

    def health_check(self) -> bool:
        url = self.config.get("url")
        if not url or not isinstance(url, str):
            return False
        try:
            return self._session(self.config).get(url, timeout=30, verify=True).status_code < 500
        except (requests.RequestException, ValueError):
            return False
