"""IRC plugin'i — kanal mesajlarını toplar."""

from __future__ import annotations

import socket
from typing import Any

from osiris.plugin import BaseCollector, CollectedItem, CollectionResult


class IrcCollector(BaseCollector):
    id = "irc"
    name = "IRC"
    network_type = "irc"

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        server = cfg.get("server")
        channels = cfg.get("channels") or []
        if not server or not channels:
            return CollectionResult(items=[], success=False, error="server ve channels gerekli")

        try:
            sock = socket.create_connection((server, cfg.get("port", 6667)), timeout=15)
            sock.settimeout(10)
            nick = cfg.get("nickname", "osiris-bot")
            sock.sendall(f"NICK {nick}\r\n".encode())
            sock.sendall(f"USER {nick} 0 * :OSIRIS\r\n".encode())

            items: list[CollectedItem] = []
            for channel in channels:
                sock.sendall(f"JOIN {channel}\r\n".encode())
            # Kısa bir süre mesajları dinle
            sock.settimeout(5)
            try:
                while True:
                    data = sock.recv(4096).decode(errors="replace")
                    if not data:
                        break
                    for line in data.splitlines():
                        if " PRIVMSG " in line:
                            items.append(
                                CollectedItem(
                                    raw_content=line,
                                    metadata={"server": server, "protocol": "irc"},
                                )
                            )
            except socket.timeout:
                pass
            sock.close()
            return CollectionResult(items=items, metadata={"server": server})
        except OSError as exc:
            return CollectionResult(items=[], success=False, error=str(exc))

    def health_check(self) -> bool:
        server = self.config.get("server")
        if not server:
            return False
        try:
            sock = socket.create_connection((server, self.config.get("port", 6667)), timeout=10)
            sock.close()
            return True
        except OSError:
            return False
