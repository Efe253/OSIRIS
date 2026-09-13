"""Matrix plugin'i — odalardan mesaj geçmişini toplar."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import assert_safe_url

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted)"}


class MatrixCollector(BaseCollector):
    id = "matrix"
    name = "Matrix"
    network_type = "matrix"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        homeserver = cfg.get("homeserver")
        room_id = cfg.get("room_id")
        if not homeserver or not room_id or not isinstance(homeserver, str) or not isinstance(room_id, str):
            return CollectionResult(items=[], success=False, error="homeserver ve room_id gerekli")
        try:
            assert_safe_url(homeserver.rstrip("/") + "/")
        except ValueError as exc:
            return CollectionResult(items=[], success=False, error=f"Güvensiz homeserver: {exc}")
        if len(room_id) > 500 or any(c in room_id for c in ("\r", "\n", "\0")):
            return CollectionResult(items=[], success=False, error="Geçersiz room_id")

        headers = dict(_HEADERS)
        if cfg.get("access_token"):
            headers["Authorization"] = f"Bearer {cfg['access_token']}"

        try:
            resp = requests.get(
                f"{homeserver.rstrip('/')}/_matrix/client/v3/rooms/{quote(room_id, safe='')}/messages",
                params={"dir": "b", "limit": 50},
                headers=headers,
                timeout=30,
                verify=True,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (401, 403):
                return CollectionResult(items=[], success=False, error="Matrix: yetkisiz")
            return CollectionResult(items=[], success=False, error=f"Matrix hatası: {type(exc).__name__}")

        try:
            payload = resp.json()
        except ValueError:
            return CollectionResult(items=[], success=False, error="Matrix: geçersiz yanıt")

        items = []
        for event in payload.get("chunk", [])[:100]:
            if not isinstance(event, dict) or event.get("type") != "m.room.message":
                continue
            body = event.get("content", {}).get("body", "") if isinstance(event.get("content"), dict) else ""
            if not body:
                continue
            items.append(
                CollectedItem(
                    raw_content=str(body)[:20_000],
                    metadata={"room": room_id[:500], "sender": str(event.get("sender", ""))[:500]},
                )
            )
        return CollectionResult(items=items, metadata={"room": room_id})

    def health_check(self) -> bool:
        homeserver = self.config.get("homeserver")
        if not homeserver or not isinstance(homeserver, str):
            return False
        try:
            assert_safe_url(homeserver.rstrip("/") + "/")
            return requests.get(
                f"{homeserver.rstrip('/')}/_matrix/client/versions", timeout=10, headers=_HEADERS, verify=True
            ).status_code < 500
        except (requests.RequestException, ValueError):
            return False
