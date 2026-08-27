"""Plugin geliştirme arayüzü.

Her veri kaynağı, BaseCollector'dan türeyen bağımsız bir plugin'tir.
Bkz. doküman §12.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import BaseModel


class CollectedItem(BaseModel):
    """Tek bir toplanan veri birimi."""

    url: Optional[str] = None
    title: Optional[str] = None
    raw_content: str
    published_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)  # type: ignore[assignment]
    tags: list[str] = field(default_factory=list)  # type: ignore[assignment]


@dataclass
class CollectionResult:
    """Bir koleksiyon görevinin sonucu."""

    items: list[CollectedItem]
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class BaseCollector:
    """Tüm collector plugin'lerinin temel sınıfı."""

    #: Plugin kimliği (manifest.json'daki id ile eşleşmeli)
    id: str = "base"
    #: Plugin adı
    name: str = "Base Collector"
    #: Ağ türü (www, tor, i2p, rss, api, ...)
    network_type: str = "www"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        """Veri toplama mantığı. Alt sınıflar tarafından uygulanır."""
        raise NotImplementedError

    def health_check(self) -> bool:
        """Kaynak erişilebilirlik testi."""
        return True

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Yapılandırma doğrulama. Hatalı alan adlarını döndürür."""
        return []
