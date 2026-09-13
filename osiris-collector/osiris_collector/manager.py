"""Collector Manager — plugin yükleme ve görev yönetimi."""

from __future__ import annotations

import importlib.util
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from osiris.plugin import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)

_MAX_QUEUE_ITEM_BYTES = 512_000
_CRON_PART_RE = re.compile(r"^[\d,/*-]+$")


class CollectorManager:
    """Plugin'leri yükler, zamanlar ve koleksiyon görevlerini çalıştırır."""

    def __init__(
        self,
        plugins_dir: str | Path = "plugins",
        redis_url: str = "redis://localhost:6379/0",
        queue_name: str = "osiris:raw_items",
    ) -> None:
        self.plugins_dir = Path(plugins_dir)
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.queue_name = queue_name
        self.plugins: dict[str, BaseCollector] = {}
        self.scheduler = BackgroundScheduler()

    def load_plugins(self) -> int:
        """plugins/ dizinindeki tüm plugin'leri yükler."""
        loaded = 0
        if not self.plugins_dir.is_dir():
            logger.error("Plugin dizini bulunamadı: %s", self.plugins_dir)
            return 0
        for manifest_path in sorted(self.plugins_dir.glob("*/manifest.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("manifest okunamadı %s: %s", manifest_path, exc)
                continue
            plugin_id = manifest.get("id")
            if not plugin_id or not isinstance(plugin_id, str):
                logger.error("Geçersiz manifest (id yok): %s", manifest_path)
                continue
            if plugin_id in self.plugins:
                logger.warning("Plugin zaten yüklü, atlanıyor: %s", plugin_id)
                continue
            collector_path = manifest_path.parent / "collector.py"
            if not collector_path.is_file():
                logger.error("collector.py bulunamadı: %s", plugin_id)
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"{plugin_id.replace('-', '_')}_collector", collector_path
                )
                if spec is None or spec.loader is None:
                    raise ImportError("modül spec oluşturulamadı")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                collector_cls = self._find_collector(module)
                self.plugins[plugin_id] = collector_cls()
            except Exception as exc:  # noqa: BLE001
                logger.error("Plugin yüklenemedi %s: %s", plugin_id, exc)
                continue
            logger.info("Plugin yüklendi: %s", plugin_id)
            loaded += 1
        return loaded

    @staticmethod
    def _find_collector(module: Any) -> type[BaseCollector]:
        for attr in vars(module).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseCollector)
                and attr is not BaseCollector
            ):
                return attr
        raise ValueError("collector sınıfı bulunamadı")

    def run_collection(self, plugin_id: str, config: dict[str, Any]) -> CollectionResult:
        """Tek bir koleksiyon görevi çalıştırır ve sonucu kuyruğa iletir."""
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            raise KeyError(f"Plugin bulunamadı: {plugin_id}")
        if not isinstance(config, dict):
            return CollectionResult(items=[], success=False, error="config dict olmalı")

        start = time.monotonic()
        try:
            result = plugin.collect(config)
        except Exception as exc:  # noqa: BLE001 — plugin crash'i yöneticiyi düşürmemeli
            logger.exception("%s: plugin çöktü", plugin_id)
            return CollectionResult(items=[], success=False, error=f"plugin hatası: {exc}")
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if result.success:
            enqueued = 0
            for item in result.items:
                try:
                    payload = json.dumps(
                        {
                            "plugin_id": plugin_id,
                            "item": item.model_dump(),
                            "collected_at": time.time(),
                        },
                        ensure_ascii=False,
                    )
                except (TypeError, ValueError) as exc:
                    logger.warning("%s: öğe serileştirilemedi: %s", plugin_id, exc)
                    continue
                if len(payload.encode("utf-8")) > _MAX_QUEUE_ITEM_BYTES:
                    logger.warning("%s: öğe çok büyük, atlandı", plugin_id)
                    continue
                try:
                    self.redis.rpush(self.queue_name, payload)
                    enqueued += 1
                except redis.RedisError as exc:
                    logger.error("%s: kuyruğa yazılamadı: %s", plugin_id, exc)
                    return CollectionResult(
                        items=result.items, success=False, error=f"kuyruk hatası: {exc}"
                    )
            logger.info(
                "%s: %d öğe toplandı (%d ms, %d kuyrukta)",
                plugin_id,
                len(result.items),
                elapsed_ms,
                enqueued,
            )
        else:
            logger.warning("%s: başarısız — %s", plugin_id, result.error)
        return result

    def schedule(self, plugin_id: str, cron: str, config: dict[str, Any]) -> None:
        """Bir plugin için cron tabanlı zamanlama ekler (5 alanlı cron)."""
        trigger = self._cron_trigger(cron)
        self.scheduler.add_job(
            self.run_collection,
            trigger,
            args=[plugin_id, config],
            id=f"{plugin_id}-{cron}",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        logger.info("Zamanlandı: %s (%s)", plugin_id, cron)

    @staticmethod
    def _cron_trigger(cron: str) -> CronTrigger:
        """'m h dom mon dow' cron ifadesini doğrular ve trigger üretir."""
        parts = cron.strip().split()
        if len(parts) != 5 or any(not _CRON_PART_RE.match(p) for p in parts):
            raise ValueError(f"Geçersiz cron (5 alan gerekli): {cron!r}")
        minute, hour, day, month, dow = parts
        return CronTrigger(
            minute=minute, hour=hour, day=day, month=month, day_of_week=dow
        )

    def start(self) -> None:
        self.scheduler.start()
        logger.info("Collector Manager başlatıldı")

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Collector Manager durduruldu")
