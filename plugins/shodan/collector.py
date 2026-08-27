"""Shodan plugin'i — internet tarama API entegrasyonu."""

from __future__ import annotations

from typing import Any

import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class ShodanCollector(BaseCollector):
    id = "shodan"
    name = "Shodan"
    network_type = "api"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        api_key = cfg.get("api_key")
        query = cfg.get("query")
        if not api_key or not query:
            return CollectionResult(items=[], success=False, error="api_key ve query gerekli")

        try:
            resp = requests.get(
                "https://api.shodan.io/shodan/host/search",
                params={"key": api_key, "query": query},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        items = []
        for match in resp.json().get("matches", []):
            items.append(
                CollectedItem(
                    url=f"http://{match.get('ip_str')}:{match.get('port')}",
                    title=match.get("product"),
                    raw_content=str(match),
                    metadata={"ip": match.get("ip_str"), "port": match.get("port")},
                )
            )
        return CollectionResult(items=items, metadata={"query": query})

    def health_check(self) -> bool:
        return bool(self.config.get("api_key"))
