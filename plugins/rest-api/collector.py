"""REST API plugin'i — JSON tabanlı API veri toplama."""

from __future__ import annotations

from typing import Any

import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


def _dig(obj: Any, path: str) -> Any:
    """Nokta ile ayrılmış JSON yolu üzerinde gezinir."""
    for part in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdigit():
            obj = obj[int(part)]
        else:
            return None
    return obj


class RestApiCollector(BaseCollector):
    id = "rest-api"
    name = "REST API"
    network_type = "api"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        endpoint = cfg.get("endpoint")
        if not endpoint:
            return CollectionResult(items=[], success=False, error="endpoint gerekli")

        try:
            resp = requests.request(
                cfg.get("method", "GET"),
                endpoint,
                headers=cfg.get("headers", {}),
                params=cfg.get("params", {}),
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        data = resp.json()
        json_path = cfg.get("json_path")
        if json_path:
            data = _dig(data, json_path)

        if not isinstance(data, list):
            data = [data]

        items = []
        for record in data:
            items.append(
                CollectedItem(
                    url=endpoint,
                    title=record.get("title") if isinstance(record, dict) else None,
                    raw_content=str(record),
                    metadata={"endpoint": endpoint},
                )
            )
        return CollectionResult(items=items, metadata={"endpoint": endpoint})

    def health_check(self) -> bool:
        endpoint = self.config.get("endpoint")
        if not endpoint:
            return False
        try:
            return requests.head(endpoint, timeout=10).status_code < 500
        except requests.RequestException:
            return False
