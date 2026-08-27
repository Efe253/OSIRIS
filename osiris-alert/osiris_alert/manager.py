"""Alert Manager — kayıtlı sorguları izler ve uyarı üretir.

Bkz. doküman §5.6.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import redis

logger = logging.getLogger(__name__)


class AlertManager:
    """Kayıtlı sorguları yeni veriyle eşleştirir ve uyarı kanallarına iletir."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        channel: str = "osiris:alerts",
    ) -> None:
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.channel = channel
        self._handlers: list[Callable[[dict[str, Any]], None]] = []

    def register_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Uyarı işleyici kaydeder (e-posta, webhook, Telegram vb.)."""
        self._handlers.append(handler)

    def check_item(self, item: dict[str, Any], saved_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Yeni bir öğeyi kayıtlı sorgularla eşleştirir."""
        triggered: list[dict[str, Any]] = []
        content = (item.get("cleaned_content") or "").lower()
        title = (item.get("title") or "").lower()

        for query in saved_queries:
            if not query.get("alert_enabled"):
                continue
            needle = (query.get("query_text") or "").lower()
            if needle and (needle in content or needle in title):
                alert = {
                    "query_id": query.get("id"),
                    "query_name": query.get("name"),
                    "item_id": item.get("id"),
                    "matched": needle,
                }
                triggered.append(alert)
                self._emit(alert)
        return triggered

    def _emit(self, alert: dict[str, Any]) -> None:
        payload = json.dumps(alert, ensure_ascii=False)
        self.redis.publish(self.channel, payload)
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as exc:  # noqa: BLE001
                logger.error("Uyarı işleyici hatası: %s", exc)
        logger.info("Uyarı tetiklendi: %s", alert.get("query_name"))
