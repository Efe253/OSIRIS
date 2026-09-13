"""Processing Pipeline CLI — kuyruk işçisi.

Kullanım:
  osiris-pipeline --once                # kuyruğu bir kez boşalt
  osiris-pipeline --loop --interval 10  # sürekli çalış (Ctrl+C ile dur)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from osiris_pipeline.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


def build_pipeline(args: argparse.Namespace) -> ProcessingPipeline:
    return ProcessingPipeline(
        redis_url=args.redis_url,
        queue_name=args.queue,
        database_url=args.database_url,
        embedding_model=args.embedding_model,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="osiris-pipeline", description="OSIRIS Processing Pipeline işçisi")
    parser.add_argument("--redis-url",
                        default=os.getenv("OSIRIS_REDIS_URL", "redis://localhost:6379/0"))
    parser.add_argument("--queue", default="osiris:raw_items")
    parser.add_argument("--database-url", default=os.getenv("OSIRIS_DATABASE_URL"))
    parser.add_argument("--embedding-model", default=os.getenv("OSIRIS_EMBEDDING_MODEL"))
    parser.add_argument("--batch", type=int, default=50)
    parser.add_argument("--once", action="store_true", help="Tek tur çalışıp çık")
    parser.add_argument("--loop", action="store_true", help="Sürekli çalış")
    parser.add_argument("--interval", type=int, default=10, help="Tur arası saniye")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if args.batch < 1 or args.batch > 1000:
        parser.error("--batch 1-1000 aralığında olmalı")
    if args.interval < 1 or args.interval > 3600:
        parser.error("--interval 1-3600 aralığında olmalı")

    pipeline = build_pipeline(args)
    if args.once or not args.loop:
        total = pipeline.run(batch_size=args.batch)
        print(f"{total} kayıt işlendi")
        return 0
    logger.info("Pipeline döngüsü başladı (her %ds)", args.interval)
    try:
        while True:
            total = pipeline.run(batch_size=args.batch)
            if total:
                logger.info("%d kayıt işlendi", total)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Durduruldu")
        return 0


if __name__ == "__main__":
    sys.exit(main())
