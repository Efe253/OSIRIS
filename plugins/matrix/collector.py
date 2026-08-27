"""Matrix plugin'i — odalardan mesaj geçmişini toplar."""

from __future__ import annotations

from typing import Any

import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class MatrixCollector(BaseCollector):
    id = "matrix"
    name = "Matrix"
    network_type = "matrix"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        homeserver = cfg.get("homeserver")
        room_id = cfg.get("room_id")
        if not homeserver or not room_id:
            return CollectionResult(items=[], success=False, error="homeserver ve room_id gerekli")

        headers = {}
        if cfg.get("access_token"):
            headers["Authorization"] = f"Bearer {cfg['access_token']}"

        try:
            resp = requests.get(
                f"{homeserver}/_matrix/client/v3/rooms/{room_id}/messages",
                params={"dir": "b", "limit": 50},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        items = []
        for event in resp.json().get("chunk", []):
            if event.get("type") != "m.room.message":
                continue
            body = event.get("content", {}).get("body", "")
            if not body:
                continue
            items.append(
                CollectedItem(
                    raw_content=body,
                    published_at=event.get("origin_server_ts"),
                    metadata={"room": room_id, "sender": event.get("sender")},
                )
            )
        return CollectionResult(items=items, metadata={"room": room_id})

    def health_check(self) -> bool:
        homeserver = self.config.get("homeserver")
        if not homeserver:
            return False
        try:
            return requests.get(f"{homeserver}/_matrix/client/versions", timeout=10).status_code < 500
        except requests.RequestException:
            return False
