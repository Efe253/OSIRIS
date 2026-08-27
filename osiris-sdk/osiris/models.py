"""Ortak veri modelleri (doküman §9 ile uyumlu)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Veri kaynağı (doküman §7.1)."""

    id: Optional[str] = None
    name: str
    url: Optional[str] = None
    network_type: str = "www"
    plugin_id: str
    auth_config: dict[str, Any] = Field(default_factory=dict)
    proxy_config: dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None
    priority: int = 5
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    """Çıkarılan varlık (doküman §9)."""

    id: Optional[str] = None
    type: str
    value: str
    normalized_value: Optional[str] = None
    confidence: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Item(BaseModel):
    """Toplanan veri birimi (doküman §9)."""

    id: Optional[str] = None
    source_id: Optional[str] = None
    raw_content: str
    cleaned_content: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    language: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    content_hash: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
