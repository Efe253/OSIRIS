"""Processing Pipeline — aşamalı veri işleme.

Aşamalar (doküman §5.3):
1. Temizleme    — HTML soyutlama, boşluk normalizasyonu
2. Dil Tespiti  — otomatik dil etiketleme
3. Varlık Çıkarma (NER)
4. Sınıflandırma
5. Embedding    — semantik vektör
6. İlişkilendirme
7. Depolama     — PostgreSQL'e yazma
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

import redis
from bs4 import BeautifulSoup
from langdetect import detect

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b")


class ProcessingPipeline:
    """Kuyruktan ham veriyi alır, işler ve veritabanına yazar."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        queue_name: str = "osiris:raw_items",
        database_url: str | None = None,
    ) -> None:
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.queue_name = queue_name
        self.database_url = database_url
        self._nlp = None

    @property
    def nlp(self):
        """spaCy modelini tembel yükleme."""
        if self._nlp is None:
            import spacy

            self._nlp = spacy.load("xx_ent_wiki_sm")
        return self._nlp

    def process_one(self, raw: str) -> dict[str, Any]:
        """Tek bir ham kaydı tüm aşamalardan geçirir."""
        payload = json.loads(raw)
        item = payload["item"]
        plugin_id = payload["plugin_id"]

        cleaned = self.clean(item.get("raw_content", ""))
        language = self.detect_language(cleaned)
        entities = self.extract_entities(cleaned)
        content_hash = hashlib.sha256(cleaned.encode()).hexdigest()

        return {
            "plugin_id": plugin_id,
            "item": {
                **item,
                "cleaned_content": cleaned,
                "language": language,
                "content_hash": content_hash,
            },
            "entities": entities,
        }

    def clean(self, text: str) -> str:
        """HTML soyutlama ve boşluk normalizasyonu."""
        soup = BeautifulSoup(text, "html.parser")
        plain = soup.get_text(" ", strip=True)
        return _WHITESPACE_RE.sub(" ", plain).strip()

    def detect_language(self, text: str) -> str:
        """Dil tespiti."""
        if not text:
            return "unknown"
        try:
            return detect(text[:500])
        except Exception:  # noqa: BLE001
            return "unknown"

    def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """Varlık çıkarma: email, IP, domain + spaCy NER."""
        entities: list[dict[str, Any]] = []

        for match in _EMAIL_RE.finditer(text):
            entities.append({"type": "email", "value": match.group(0)})
        for match in _IP_RE.finditer(text):
            entities.append({"type": "ip", "value": match.group(0)})
        for match in _DOMAIN_RE.finditer(text):
            entities.append({"type": "domain", "value": match.group(0)})

        try:
            doc = self.nlp(text[:10000])
            for ent in doc.ents:
                entities.append({"type": ent.label_.lower(), "value": ent.text})
        except Exception:  # noqa: BLE001
            logger.debug("NER başarısız, regex sonuçları kullanılıyor")

        return entities

    def run(self, batch_size: int = 10) -> int:
        """Kuyruktan batch halinde kayıt işler. İşlenen kayıt sayısını döndürür."""
        processed = 0
        for _ in range(batch_size):
            raw = self.redis.lpop(self.queue_name)
            if raw is None:
                break
            result = self.process_one(raw)
            self.store(result)
            processed += 1
        return processed

    def store(self, result: dict[str, Any]) -> None:
        """İşlenmiş veriyi PostgreSQL'e yazar."""
        if not self.database_url:
            logger.debug("database_url yok, depolama atlandı")
            return
        # Faz 1: depolama iskeleti. Tam SQL yazımı Faz 2'de eklenecek.
        logger.info("Depolanacak: %s", result["item"]["content_hash"][:12])
