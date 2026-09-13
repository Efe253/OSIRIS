"""Blockchain plugin'i — zincir üstü veri toplama."""

from __future__ import annotations

import re
from typing import Any

import requests
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import assert_safe_url, fetch_url

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted)"}
_ADDRESS_RE = re.compile(r"^[A-Za-z0-9]{20,100}$")
# Sabit allowlist: kullanıcı girdisi host'a değil yola eklenir (SSRF güvenli)
_BLOCKSTREAM_BASE = "https://blockstream.info/api"


class BlockchainCollector(BaseCollector):
    id = "blockchain"
    name = "Blockchain"
    network_type = "blockchain"

    def _rpc(self, rpc_url: str, method: str, params: list) -> Any:
        resp = fetch_url(
            requests, "POST", rpc_url,
            json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
            timeout=30,
            headers=_HEADERS,
            verify=True,
            max_bytes=1_000_000,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("RPC: beklenmeyen yanıt biçimi")
        return data.get("result")

    def _evm_address(self, rpc_url: str, chain: str, address: str) -> list[CollectedItem]:
        if not address.startswith("0x") or len(address) != 42:
            return []
        balance = self._rpc(rpc_url, "eth_getBalance", [address, "latest"])
        txcount = self._rpc(rpc_url, "eth_getTransactionCount", [address, "latest"])
        return [CollectedItem(
            raw_content=f"address={address} balance_wei={balance} txcount={txcount}"[:1000],
            metadata={"chain": chain, "address": address},
            tags=["crypto"],
        )]

    def _btc_address(self, address: str) -> list[CollectedItem]:
        resp = fetch_url(
            requests, "GET", f"{_BLOCKSTREAM_BASE}/address/{address}",
            timeout=30, headers=_HEADERS, verify=True, max_bytes=1_000_000,
        )
        resp.raise_for_status()
        info = resp.json()
        if not isinstance(info, dict):
            raise ValueError("Blockstream: beklenmeyen yanıt")
        funded = info.get("chain_stats", {}).get("funded_txo_sum", 0)
        spent = info.get("chain_stats", {}).get("spent_txo_sum", 0)
        txs = info.get("chain_stats", {}).get("tx_count", 0)
        return [CollectedItem(
            raw_content=f"address={address} balance_sat={funded - spent} txcount={txs}"[:1000],
            metadata={"chain": "bitcoin", "address": address},
            tags=["crypto"],
        )]

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        chain = str(cfg.get("chain", "ethereum"))[:50].lower()
        address = cfg.get("address")
        if address is not None:
            if not isinstance(address, str) or not _ADDRESS_RE.match(address):
                return CollectionResult(items=[], success=False, error="Geçersiz adres")
            try:
                if chain == "bitcoin":
                    items = self._btc_address(address)
                else:
                    rpc_url = cfg.get("rpc_url")
                    if not isinstance(rpc_url, str):
                        return CollectionResult(items=[], success=False, error="rpc_url gerekli")
                    assert_safe_url(rpc_url)
                    items = self._evm_address(rpc_url, chain, address)
            except ValueError as exc:
                return CollectionResult(items=[], success=False, error=f"Adres sorgusu: {exc}"[:300])
            except requests.RequestException as exc:
                return CollectionResult(items=[], success=False, error=f"Adres sorgusu: {type(exc).__name__}")
            return CollectionResult(items=items, metadata={"chain": chain, "address": address})

        rpc_url = cfg.get("rpc_url")
        if not rpc_url or not isinstance(rpc_url, str):
            return CollectionResult(items=[], success=False, error="rpc_url gerekli")
        try:
            assert_safe_url(rpc_url)
        except ValueError as exc:
            return CollectionResult(items=[], success=False, error=f"Güvensiz rpc_url: {exc}")

        try:
            block_number = self._rpc(rpc_url, "eth_blockNumber", [])
        except requests.RequestException as exc:
            return CollectionResult(items=[], success=False, error=f"RPC hatası: {type(exc).__name__}")
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
            resp = fetch_url(
                requests, "POST", rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=10,
                headers=_HEADERS,
                verify=True,
                max_bytes=65536,
            )
            return resp.status_code < 500
        except (requests.RequestException, ValueError):
            return False
