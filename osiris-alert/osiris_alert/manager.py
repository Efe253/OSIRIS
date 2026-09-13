"""Alert Manager — kayıtlı sorguları izler ve uyarı üretir.

Bkz. doküman §5.6.
"""

from __future__ import annotations

import json
import logging
import math
from collections import defaultdict, deque
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
        anomaly_window: int = 100,
        anomaly_threshold: float = 3.0,
        anomaly_min_samples: int = 10,
    ) -> None:
        # redis_url=None → yayın yapma (test/offline modu), handler'lar yine çalışır
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None
        self.channel = channel
        self._handlers: list[Callable[[dict[str, Any]], None]] = []
        self._muted: set[str] = set()
        # Anomali bazı: metrik adı → kayan pencere (yalnızca bellek-içi)
        self._anomaly_window = max(10, min(int(anomaly_window), 10_000))
        self._anomaly_threshold = max(0.5, min(float(anomaly_threshold), 10.0))
        self._anomaly_min_samples = max(5, min(int(anomaly_min_samples), 1000))
        self._baselines: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self._anomaly_window)
        )

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

    def record_metric(self, name: str, value: float) -> None:
        """Anomali tabanı için ölçüm kaydeder (örn. saatlik öğe sayısı)."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(v):
            return
        self._baselines[str(name)[:200]].append(v)

    def check_anomaly(self, name: str, value: float) -> dict[str, Any] | None:
        """z-skoru eşiği aşarsa uyarı sözlüğü döner (yoksa None).

        Isınma dönemi (min_samples) dolmadan None döner. Yeni değer tabana
        DAHİL EDİLMEZ — önce kontrol edilir, çağrıcı record_metric çağırır.
        """
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(v):
            return None
        samples = self._baselines.get(str(name)[:200], deque())
        if len(samples) < self._anomaly_min_samples:
            return None
        mean = sum(samples) / len(samples)
        var = sum((s - mean) ** 2 for s in samples) / len(samples)
        stdev = math.sqrt(var)
        if stdev == 0:
            anomalous = v != mean
            z = math.inf if anomalous else 0.0
        else:
            z = (v - mean) / stdev
            anomalous = abs(z) > self._anomaly_threshold
        if not anomalous:
            return None
        alert = {
            "metric": str(name)[:200],
            "value": v,
            "mean": mean,
            "stdev": stdev,
            "z_score": z,
            "samples": len(samples),
        }
        self._emit(alert)
        return alert

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
