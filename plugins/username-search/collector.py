"""Username Search plugin'i — Maigret tarzı profil taraması.

Verilen kullanıcı adını site DB'sindeki profil URL'lerinde yoklar:
- status_code: 200 (+absence yok) = bulundu, 404 = yok
- message: presenceStrs/absenceStrs eşleşmesi
- response_url: son URL kullanıcı adını içeriyorsa bulundu
Site DB'si Maigret data.json uyumludur (sites_db ile tam DB verilebilir).
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris.security import fetch_url

_HEADERS = {"User-Agent": "OSIRIS-OSINT/0.1 (+self-hosted)"}
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{1,63}$")
_DEFAULT_DB = Path(__file__).parent / "sites.json"


class UsernameSearchCollector(BaseCollector):
    id = "username-search"
    name = "Username Search"
    network_type = "www"

    def load_sites(self, db_path: str | Path | None = None) -> dict[str, dict]:
        """Site DB'sini yükler (Maigret uyumlu)."""
        path = Path(db_path) if db_path else _DEFAULT_DB
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Site DB okunamadı: {exc}") from exc
        sites = {}
        for name, rule in data.items():
            if name.startswith("_") or not isinstance(rule, dict):
                continue
            url = rule.get("url", "")
            if "{username}" not in str(url):
                continue
            sites[str(name)] = {
                "url": str(url),
                "check_type": str(rule.get("checkType", "status_code")),
                "presence": [str(s) for s in rule.get("presenceStrs", [])][:10],
                "absence": [str(s) for s in rule.get("absenceStrs", [])][:10],
                "tags": [str(t) for t in rule.get("tags", [])][:10],
            }
        return sites

    def _check_one(self, site: str, rule: dict, username: str,
                   timeout: int) -> CollectedItem | None:
        """Tek siteyi yoklar. Bulunursa öğe, yoksa/bilinmezse None."""
        profile_url = rule["url"].replace("{username}", quote(username, safe=""))
        session = requests.Session()
        session.headers.update(_HEADERS)
        try:
            resp = fetch_url(session, "GET", profile_url, timeout=timeout,
                             verify=True, max_bytes=500_000)
        except (requests.RequestException, ValueError):
            return None  # erişilemez = bilinmiyor, sessiz geç
        finally:
            session.close()
        check = rule["check_type"]
        found = False
        if check == "status_code":
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                return None
            body = resp.text[:50_000]
            if any(a in body for a in rule["absence"]):
                return None
            found = True
        elif check == "message":
            body = resp.text[:50_000]
            if any(p in body for p in rule["presence"]):
                found = True
            elif any(a in body for a in rule["absence"]):
                return None
            else:
                return None
        elif check == "response_url":
            final_url = getattr(resp, "url", "") or ""
            found = username.lower() in final_url.lower()
            if not found:
                return None
        else:
            return None
        if not found:
            return None
        return CollectedItem(
            url=profile_url[:2048],
            title=f"{username} @ {site}"[:500],
            raw_content=f"Profil bulundu: {site} — {profile_url}"[:2000],
            metadata={"site": site, "username": username, "check": check},
            tags=["username", *rule["tags"][:5]],
        )

    def collect(self, config: dict[str, Any] | None = None) -> CollectionResult:
        cfg = config or self.config
        username = cfg.get("username")
        if not username or not isinstance(username, str) or not _USERNAME_RE.match(username):
            return CollectionResult(items=[], success=False, error="Geçersiz username")
        try:
            sites = self.load_sites(cfg.get("sites_db"))
        except ValueError as exc:
            return CollectionResult(items=[], success=False, error=str(exc))
        only = cfg.get("sites")
        if isinstance(only, list) and only:
            wanted = {str(s) for s in only}
            sites = {k: v for k, v in sites.items() if k in wanted}
        tags = cfg.get("tags")
        if isinstance(tags, list) and tags:
            wanted_tags = {str(t) for t in tags}
            sites = {k: v for k, v in sites.items()
                     if wanted_tags & set(v["tags"])}
        try:
            max_sites = max(1, min(int(cfg.get("max_sites", 200)), 3000))
        except (TypeError, ValueError):
            max_sites = 200
        try:
            workers = max(1, min(int(cfg.get("workers", 10)), 20))
        except (TypeError, ValueError):
            workers = 10
        try:
            timeout = max(5, min(int(cfg.get("timeout", 15)), 30))
        except (TypeError, ValueError):
            timeout = 15
        names = sorted(sites)[:max_sites]
        items: list[CollectedItem] = []
        unknown = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self._check_one, n, sites[n], username, timeout): n
                       for n in names}
            for future in as_completed(futures):
                try:
                    found = future.result()
                except Exception:  # noqa: BLE001 — tek site tüm taramayı düşürmez
                    unknown += 1
                    continue
                if found is None:
                    unknown += 1
                else:
                    items.append(found)
        items.sort(key=lambda i: i.metadata.get("site", ""))
        return CollectionResult(
            items=items,
            metadata={"username": username, "checked": len(names),
                      "found": len(items), "unknown": unknown},
        )

    def health_check(self) -> bool:
        try:
            return len(self.load_sites()) > 0
        except ValueError:
            return False
