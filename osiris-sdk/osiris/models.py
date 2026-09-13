"""Ortak veri modelleri (doküman §9 ile uyumlu)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Veri kaynağı (doküman §7.1)."""

    id: str | None = None
    name: str
    url: str | None = None
    network_type: str = "www"
    plugin_id: str
    auth_config: dict[str, Any] = Field(default_factory=dict)
    proxy_config: dict[str, Any] = Field(default_factory=dict)
    schedule: str | None = None
    priority: int = 5
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    """Çıkarılan varlık (doküman §9)."""

    id: str | None = None
    type: str
    value: str
    normalized_value: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    """Toplanan veri birimi (doküman §9)."""

    id: str | None = None
    source_id: str | None = None
    raw_content: str
    cleaned_content: str | None = None
    url: str | None = None
    title: str | None = None
    language: str | None = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
