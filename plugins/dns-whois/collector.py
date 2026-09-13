"""DNS & WHOIS plugin'i — pasif keşif."""

from __future__ import annotations

import socket
from typing import Any

import dns.exception
import dns.resolver

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import sanitize_domain, sanitize_hostname

_ALLOWED_RTYPE = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR", "SRV"}


class DnsWhoisCollector(BaseCollector):
    id = "dns-whois"
    name = "DNS & WHOIS"
    network_type = "api"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        raw_domain = cfg.get("domain")
        if not raw_domain or not isinstance(raw_domain, str):
            return CollectionResult(items=[], success=False, error="domain gerekli")
        try:
            domain = sanitize_domain(raw_domain)
        except ValueError as exc:
            return CollectionResult(items=[], success=False, error=f"Geçersiz domain: {exc}")

        record_types = cfg.get("record_types", ["A", "AAAA", "MX", "NS", "TXT"])
        if not isinstance(record_types, list):
            return CollectionResult(items=[], success=False, error="record_types liste olmalı")
        record_types = [str(r).upper() for r in record_types[:10] if str(r).upper() in _ALLOWED_RTYPE]
        if not record_types:
            record_types = ["A"]
        items: list[CollectedItem] = []

        resolver = dns.resolver.Resolver()
        resolver.lifetime = 10
        for rtype in record_types:
            try:
                answers = resolver.resolve(domain, rtype)
                for answer in list(answers)[:50]:
                    items.append(
                        CollectedItem(
                            raw_content=str(answer)[:5000],
                            metadata={"domain": domain, "record_type": rtype},
                        )
                    )
            except dns.resolver.NoAnswer:
                continue
            except dns.resolver.NXDOMAIN:
                return CollectionResult(items=[], success=False, error="Domain bulunamadı")
            except dns.exception.DNSException as exc:
                return CollectionResult(items=[], success=False, error=str(exc)[:500])

        # WHOIS (basit TCP 43 sorgusu, yanıta üst sınır)
        try:
            whois = self._whois(domain)
            if whois:
                items.append(
                    CollectedItem(raw_content=whois[:20_000], metadata={"domain": domain, "record_type": "WHOIS"})
                )
        except OSError:
            pass

        return CollectionResult(items=items[:100], metadata={"domain": domain})

    @staticmethod
    def _whois(domain: str) -> str:
        domain = sanitize_domain(domain)
        with socket.create_connection(("whois.iana.org", 43), timeout=10) as sock:
            sock.settimeout(10)
            sock.sendall(f"{domain}\r\n".encode("ascii"))
            data = b""
            while len(data) < 50_000:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                data += chunk
        return data.decode(errors="replace")

    def health_check(self) -> bool:
        try:
            sanitize_hostname(str(self.config.get("domain", "")))
            return bool(self.config.get("domain"))
        except ValueError:
            return False
