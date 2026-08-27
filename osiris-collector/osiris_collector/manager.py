"""Collector Manager — plugin yükleme ve görev yönetimi."""

from __future__ import annotations

import importlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import redis
from apscheduler.schedulers.background import BackgroundScheduler

from osiris.plugin import BaseCollector, CollectionResult

logger = logging.getLogger(__name__)


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
        for manifest_path in self.plugins_dir.glob("*/manifest.json"):
            manifest = json.loads(manifest_path.read_text())
            plugin_id = manifest["id"]
            collector_path = manifest_path.parent / "collector.py"
            if not collector_path.exists():
                logger.error("collector.py bulunamadı: %s", plugin_id)
                continue
            spec = importlib.util.spec_from_file_location(
                f"{plugin_id.replace('-', '_')}_collector", collector_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            collector_cls = self._find_collector(module)
            self.plugins[plugin_id] = collector_cls()
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

        start = time.monotonic()
        result = plugin.collect(config)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if result.success:
            for item in result.items:
                self.redis.rpush(
                    self.queue_name,
                    json.dumps(
                        {
                            "plugin_id": plugin_id,
                            "item": item.model_dump(),
                            "collected_at": time.time(),
                        }
                    ),
                )
            logger.info(
                "%s: %d öğe toplandı (%d ms)",
                plugin_id,
                len(result.items),
                elapsed_ms,
            )
        else:
            logger.warning("%s: başarısız — %s", plugin_id, result.error)
        return result

    def schedule(self, plugin_id: str, cron: str, config: dict[str, Any]) -> None:
        """Bir plugin için cron tabanlı zamanlama ekler."""
        hour, minute = self._parse_cron(cron)
        self.scheduler.add_job(
            self.run_collection,
            "cron",
            hour=hour,
            minute=minute,
            args=[plugin_id, config],
            id=f"{plugin_id}-{cron}",
            replace_existing=True,
        )
        logger.info("Zamanlandı: %s (%s)", plugin_id, cron)

    @staticmethod
    def _parse_cron(cron: str) -> tuple[int, int]:
        """Basit 'm h * * *' cron ayrıştırma. Faz 2'de tam destek eklenecek."""
        parts = cron.split()
        minute = int(parts[0]) if parts[0].isdigit() else 0
        hour = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        return hour, minute

    def start(self) -> None:
        self.scheduler.start()
        logger.info("Collector Manager başlatıldı")

    def shutdown(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Collector Manager durduruldu")
