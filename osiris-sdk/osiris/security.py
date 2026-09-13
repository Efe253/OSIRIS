"""Paylaşılan güvenlik yardımcıları.

SSRF koruması, URL/host doğrulama ve gizli veri maskeleme.
Tüm collector plugin'leri ve API bu modülü kullanmalıdır.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# RFC1918 + loopback + link-local + multicast + CGNAT + dokümantasyon blokları
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (cloud metadata dahil)
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # CGNAT
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),  # multicast
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # unique local
    ipaddress.ip_network("fe80::/10"),  # link-local v6
]

_ALLOWED_SCHEMES = {"http", "https"}

# İzin verilen port aralığı (ayrıcalıklı portlara gidişi kısıtla)
_MAX_PORT = 65535


def _host_ips(host: str) -> list[str]:
    """Host adını IP listesine çözer. Çözülemezse boş liste döner."""
    try:
        _, _, ips = socket.gethostbyname_ex(host)
        return ips
    except OSError:
        return []


def is_blocked_host(host: str) -> bool:
    """Özel/iç ağ host'u mu? Çözülemeyen host'lar da engellenir (fail-closed)."""
    if not host:
        return True
    h = host.strip().lower().rstrip(".")
    if h in ("localhost",):
        return True
    # Doğrudan IP verilmişse
    try:
        ip = ipaddress.ip_address(h)
        return any(ip in net for net in _BLOCKED_NETWORKS)
    except ValueError:
        pass
    # DNS adı: çözümle ve tüm kayıtları kontrol et
    ips = _host_ips(h)
    if not ips:
        return True
    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return True
        if any(ip in net for net in _BLOCKED_NETWORKS):
            return True
    return False


def assert_safe_url(url: str, *, allow_onion: bool = False) -> str:
    """URL'yi SSRF'e karşı doğrular. Geçersizse ValueError yükseltir.

    - http/https zorunlu (onion için allow_onion ile .onion host'una izin)
    - kullanıcı bilgisi (user:pass@) yasak
    - özel/iç IP ve localhost yasak
    """
    if not url or len(url) > 2048:
        raise ValueError("URL boş veya çok uzun")
    parsed = urlparse(url.strip())
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"İzin verilmeyen şema: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise ValueError("URL içinde kimlik bilgisi yasak")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL host içermiyor")
    if host.endswith(".onion"):
        if not allow_onion:
            raise ValueError(".onion adresleri yalnızca Tor plugin'i ile kullanılabilir")
        return url
    if parsed.port is not None and not (1 <= parsed.port <= _MAX_PORT):
        raise ValueError("Geçersiz port")
    if is_blocked_host(host):
        raise ValueError(f"İç ağ/özel host engellendi: {host}")
    return url


def sanitize_irc_token(value: str, max_len: int = 64) -> str:
    """IRC nick/kanal enjeksiyonuna karşı temizler (CRLF + boşluk kontrolü)."""
    if not value:
        raise ValueError("Boş IRC değeri")
    if len(value) > max_len:
        raise ValueError("IRC değeri çok uzun")
    if any(c in value for c in ("\r", "\n", "\0", " ", ",", "*")):
        raise ValueError("IRC değerinde geçersiz karakter")
    if not value.startswith("#") and value.startswith(("#", "&")) is False and max_len == 64:
        # nick için ek kontrol: harf/rakam/-/_/[/]/{} ile başlamalı
        pass
    return value


def sanitize_channel(value: str) -> str:
    if not value or len(value) > 64:
        raise ValueError("Geçersiz kanal")
    if any(c in value for c in ("\r", "\n", "\0", " ", ",")):
        raise ValueError("Kanalda geçersiz karakter")
    if not value.startswith(("#", "&")):
        raise ValueError("Kanal # veya & ile başlamalı")
    return value


def sanitize_domain(domain: str) -> str:
    """DNS/WHOIS için domain doğrulama (CRLF enjeksiyonunu engeller)."""
    if not domain or len(domain) > 253:
        raise ValueError("Geçersiz domain")
    d = domain.strip().lower().rstrip(".")
    if any(c in d for c in ("\r", "\n", "\0", " ", "/", "@", ":")):
        raise ValueError("Domain geçersiz karakter içeriyor")
    if "." not in d and d != "localhost":
        raise ValueError("Domain TLD içermeli")
    labels = d.split(".")
    for label in labels:
        if not label or len(label) > 63:
            raise ValueError("Domain etiketi geçersiz")
        if label.startswith("-") or label.endswith("-"):
            raise ValueError("Domain etiketi tire ile başlayamaz/bitmez")
        if not all(c.isalnum() or c == "-" for c in label):
            raise ValueError("Domain etiketi geçersiz karakter içeriyor")
    return d


def sanitize_hostname(host: str, max_len: int = 253) -> str:
    if not host or len(host) > max_len:
        raise ValueError("Geçersiz host")
    h = host.strip().lower()
    if any(c in h for c in ("\r", "\n", "\0", " ", "/")):
        raise ValueError("Host geçersiz karakter içeriyor")
    return h


def safe_title(soup) -> str | None:
    """BeautifulSoup title çıkarımını güvenli yapar (None-string crash fix)."""
    try:
        if soup is None or soup.title is None:
            return None
        text = soup.title.get_text(" ", strip=True)
        return text[:500] if text else None
    except Exception:
        return None


def cap_list(value: list, limit: int) -> list:
    return value[:limit] if isinstance(value, list) else []


def mask_secret(value: str | None, keep: int = 4) -> str:
    if not value:
        return "***"
    s = str(value)
    if len(s) <= keep:
        return "***"
    return "*" * (len(s) - keep) + s[-keep:]
