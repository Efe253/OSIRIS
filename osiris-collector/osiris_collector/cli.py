"""Collector Manager CLI."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from osiris_collector.manager import CollectorManager


def main() -> int:
    parser = argparse.ArgumentParser(prog="osiris-collector", description="OSIRIS Collector Manager")
    parser.add_argument("--plugins-dir", default="plugins", help="Plugin dizini")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0", help="Redis URL")
    parser.add_argument("--list", action="store_true", help="Yüklü plugin'leri listele")
    parser.add_argument("--run", metavar="PLUGIN_ID", help="Tek bir koleksiyon görevi çalıştır")
    parser.add_argument("--config", metavar="JSON", help="Görev yapılandırması (JSON)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Ayrıntılı log")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    manager = CollectorManager(plugins_dir=args.plugins_dir, redis_url=args.redis_url)
    manager.load_plugins()

    if args.list:
        for pid, plugin in manager.plugins.items():
            print(f"{pid}\t{plugin.name}\t{plugin.network_type}")
        return 0

    if args.run:
        config = json.loads(args.config) if args.config else {}
        result = manager.run_collection(args.run, config)
        print(json.dumps(result.metadata, ensure_ascii=False))
        return 0 if result.success else 1

    manager.start()
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
