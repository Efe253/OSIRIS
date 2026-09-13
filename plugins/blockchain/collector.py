"""Blockchain plugin'i — zincir üstü veri toplama."""

from __future__ import annotations

from typing import Any

import requests

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import assert_safe_url

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted)"}


class BlockchainCollector(BaseCollector):
    id = "blockchain"
    name = "Blockchain"
    network_type = "blockchain"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        rpc_url = cfg.get("rpc_url")
        if not rpc_url or not isinstance(rpc_url, str):
            return CollectionResult(items=[], success=False, error="rpc_url gerekli")
        try:
            assert_safe_url(rpc_url)
        except ValueError as exc:
            return CollectionResult(items=[], success=False, error=f"Güvensiz rpc_url: {exc}")

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
                headers=_HEADERS,
                verify=True,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=f"RPC hatası: {type(exc).__name__}")

        try:
            block_number = resp.json().get("result")
        except ValueError:
            return CollectionResult(items=[], success=False, error="RPC: geçersiz yanıt")
        items = [
            CollectedItem(
                raw_content=f"block_number={block_number}"[:1000],
                metadata={"chain": str(cfg.get("chain", "ethereum"))[:100]},
            )
        ]
        return CollectionResult(items=items, metadata={"block_number": block_number})

    def health_check(self) -> bool:
        rpc_url = self.config.get("rpc_url")
        if not rpc_url or not isinstance(rpc_url, str):
            return False
        try:
            assert_safe_url(rpc_url)
            resp = requests.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=10,
                headers=_HEADERS,
                verify=True,
            )
            return resp.status_code < 500
        except (requests.RequestException, ValueError):
            return False
