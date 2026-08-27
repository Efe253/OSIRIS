"""Blockchain plugin'i — zincir üstü veri toplama."""

from __future__ import annotations

from typing import Any

import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class BlockchainCollector(BaseCollector):
    id = "blockchain"
    name = "Blockchain"
    network_type = "blockchain"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        rpc_url = cfg.get("rpc_url")
        if not rpc_url:
            return CollectionResult(items=[], success=False, error="rpc_url gerekli")

        try:
            resp = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                },
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

        block_number = resp.json().get("result")
        items = [
            CollectedItem(
                raw_content=f"block_number={block_number}",
                metadata={"chain": cfg.get("chain", "ethereum"), "rpc": rpc_url},
            )
        ]
        return CollectionResult(items=items, metadata={"block_number": block_number})

    def health_check(self) -> bool:
        rpc_url = self.config.get("rpc_url")
        if not rpc_url:
            return False
        try:
            resp = requests.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=10,
            )
            return resp.status_code < 500
        except requests.RequestException:
            return False
