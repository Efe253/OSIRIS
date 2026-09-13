"""Alert Manager — kayıtlı sorguları izler ve uyarı üretir.

Bkz. doküman §5.6.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import redis

logger = logging.getLogger(__name__)

_MAX_QUERY_TEXT = 500
_MAX_QUERIES_PER_ITEM = 100


class AlertManager:
    """Kayıtlı sorguları yeni veriyle eşleştirir ve uyarı kanallarına iletir."""

    def __init__(
        self,
        redis_url: str | None = "redis://localhost:6379/0",
        channel: str = "osiris:alerts",
    ) -> None:
        # redis_url=None → yayın yapma (test/offline modu), handler'lar yine çalışır
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self.channel = channel
        self._handlers: list[Callable[[dict[str, Any]], None]] = []
        self._muted: set[str] = set()

    @property
    def redis(self) -> redis.Redis | None:
        if self._redis_url is None:
            return None
        if self._redis is None:
            self._redis = redis.Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def register_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Uyarı işleyici kaydeder (e-posta, webhook, Telegram vb.)."""
        self._handlers.append(handler)

    def mute(self, query_id: str) -> None:
        self._muted.add(str(query_id))

    def unmute(self, query_id: str) -> None:
        self._muted.discard(str(query_id))

    def check_item(self, item: dict[str, Any], saved_queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Yeni bir öğeyi kayıtlı sorgularla eşleştirir."""
        triggered: list[dict[str, Any]] = []
        if not isinstance(item, dict) or not isinstance(saved_queries, list):
            return triggered
        content = str(item.get("cleaned_content") or "")[:50_000].lower()
        title = str(item.get("title") or "")[:2000].lower()

        for query in saved_queries[:_MAX_QUERIES_PER_ITEM]:
            if not isinstance(query, dict) or not query.get("alert_enabled"):
                continue
            qid = str(query.get("id") or "")
            if qid in self._muted:
                continue
            needle = str(query.get("query_text") or "").strip().lower()[:_MAX_QUERY_TEXT]
            if needle and (needle in content or needle in title):
                alert = {
                    "query_id": query.get("id"),
                    "query_name": str(query.get("name") or "")[:200],
                    "item_id": item.get("id"),
                    "matched": needle[:200],
                }
                triggered.append(alert)
                self._emit(alert)
        return triggered

    def _emit(self, alert: dict[str, Any]) -> None:
        try:
            payload = json.dumps(alert, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            logger.error("Uyarı serileştirilemedi: %s", exc)
            return
        client = self.redis
        if client is not None:
            try:
                client.publish(self.channel, payload)
            except redis.RedisError as exc:
                logger.warning("Redis yayını başarısız: %s", exc)
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as exc:  # noqa: BLE001
                logger.error("Uyarı işleyici hatası: %s", exc)
        logger.info("Uyarı tetiklendi: %s", alert.get("query_name"))
