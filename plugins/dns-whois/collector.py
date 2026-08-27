"""DNS & WHOIS plugin'i — pasif keşif."""

from __future__ import annotations

import socket
from typing import Any

import dns.resolver

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class DnsWhoisCollector(BaseCollector):
    id = "dns-whois"
    name = "DNS & WHOIS"
    network_type = "api"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        domain = cfg.get("domain")
        if not domain:
            return CollectionResult(items=[], success=False, error="domain gerekli")

        record_types = cfg.get("record_types", ["A", "AAAA", "MX", "NS", "TXT"])
        items: list[CollectedItem] = []

        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                for answer in answers:
                    items.append(
                        CollectedItem(
                            raw_content=str(answer),
                            metadata={"domain": domain, "record_type": rtype},
                        )
                    )
            except dns.resolver.NoAnswer:
                continue
            except dns.resolver.NXDOMAIN:
                return CollectionResult(items=[], success=False, error="Domain bulunamadı")
            except dns.exception.DNSException as exc:
                return CollectionResult(items=[], success=False, error=str(exc))

        # WHOIS (basit TCP 43 sorgusu)
        try:
            whois = self._whois(domain)
            if whois:
                items.append(
                    CollectedItem(raw_content=whois, metadata={"domain": domain, "record_type": "WHOIS"})
                )
        except OSError:
            pass

        return CollectionResult(items=items, metadata={"domain": domain})

    @staticmethod
    def _whois(domain: str) -> str:
        with socket.create_connection(("whois.iana.org", 43), timeout=10) as sock:
            sock.sendall(f"{domain}\r\n".encode())
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
        return data.decode(errors="replace")

    def health_check(self) -> bool:
        return bool(self.config.get("domain"))
