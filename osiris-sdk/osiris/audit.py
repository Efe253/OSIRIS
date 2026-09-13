"""Denetim logları — append-only, hash zincirli (doküman §10.4).

`audit_logs` tablosuna yazar; her kayıt bir öncekinin SHA-256 özetini içerir.
psycopg bağımlılığı almamak için DBAPI-uyumlu bir bağlantı (duck-typing)
kabul eder: yalnızca ``.cursor()`` + context manager protokolü gerekir.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _Cursor(Protocol):
    def execute(self, query: str, params: Any = ...) -> Any: ...
    def fetchone(self) -> Any: ...


class _Connection(Protocol):
    def cursor(self) -> Any: ...
    def commit(self) -> None: ...


def _canonical(user_id: str | None, action: str, resource: str | None,
               detail: dict[str, Any] | None) -> str:
    return json.dumps(
        {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "detail": detail or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _normalize(user_id: str | None, resource: str | None,
               detail: dict[str, Any] | None) -> tuple[str, str, dict[str, Any]]:
    """Saklanan değerlerle kanonik yükü aynı yapar (kesme ÖNCE yapılır)."""
    try:
        detail_json = json.loads(json.dumps(detail or {}, ensure_ascii=False, default=str))
    except (TypeError, ValueError):
        detail_json = {"_unserializable": True}
    if not isinstance(detail_json, dict):
        detail_json = {"value": detail_json}
    return (user_id or "")[:200], (resource or "")[:500], detail_json


def append_audit(conn: _Connection, user_id: str | None, action: str,
                 resource: str | None = None,
                 detail: dict[str, Any] | None = None) -> dict[str, str]:
    """Zincire yeni bir denetim kaydı ekler. ``{'prev_hash', 'hash'}`` döner."""
    if not action or len(action) > 200:
        raise ValueError("action 1-200 karakter olmalı")
    if resource is not None and len(resource) > 500:
        raise ValueError("resource çok uzun")
    user_id, resource, detail = _normalize(user_id, resource, detail)
    payload = _canonical(user_id, action, resource, detail)

    cur = conn.cursor()
    try:
        # Eşzamanlı yazıcılar zinciri çatallamasın (PostgreSQL'de işlem-kapsamlı
        # kilit; desteklemeyen sürücülerde sessizce atlanır).
        try:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext('osiris_audit_chain'))")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Danışma kilidi atlandı (PG dışı?): %s", exc)
        cur.execute("SELECT hash FROM audit_logs ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        prev_hash = row[0] if row and row[0] else "GENESIS"
        digest = hashlib.sha256(f"{prev_hash}|{payload}".encode()).hexdigest()
        cur.execute(
            """
            INSERT INTO audit_logs (user_id, action, resource, detail, prev_hash, hash)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                user_id,
                action,
                resource,
                json.dumps(detail, ensure_ascii=False, default=str),
                None if prev_hash == "GENESIS" else prev_hash,
                digest,
            ),
        )
    finally:
        close = getattr(cur, "close", None)
        if callable(close):
            close()
    conn.commit()
    return {"prev_hash": prev_hash, "hash": digest}


def verify_chain(conn: _Connection, limit: int = 1000) -> dict[str, Any]:
    """Son N kaydın zincir bütünlüğünü doğrular.

    NOT: ilk kaydın öncülü GENESIS sayılır; tablonun başından değil sonundan
    N kayıt alınır, ancak ilk N kayıttan öncesi doğrulanamazsa `truncated`
    döner (zincirin görünen kısmı tutarlıysa ok=True).
    """
    limit = max(1, min(int(limit), 100_000))
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, user_id, action, resource, detail, prev_hash, hash"
            " FROM audit_logs ORDER BY id DESC LIMIT %s",
            (limit,),
        )
        rows = list(reversed(cur.fetchall()))
    finally:
        close = getattr(cur, "close", None)
        if callable(close):
            close()
    if not rows:
        return {"ok": True, "checked": 0}
    # Pencere tablo başını içermiyorsa ilk kaydın öncülü bilinemez
    cur2 = conn.cursor()
    try:
        cur2.execute("SELECT min(id) FROM audit_logs")
        min_row = cur2.fetchone()
    finally:
        close = getattr(cur2, "close", None)
        if callable(close):
            close()
    truncated = bool(min_row and min_row[0] is not None and rows[0][0] != min_row[0])
    prev: str | None = rows[0][5]  # ilk görünen kaydın beyan ettiği öncül
    checked = 0
    for _rid, user_id, action, resource, detail, prev_hash, digest in rows:
        if prev_hash != prev:
            return {"ok": False, "checked": checked, "error": "prev_hash uyuşmazlığı"}
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except ValueError:
                detail = {}
        anchor = prev if prev is not None else "GENESIS"
        payload = _canonical(user_id, action, resource, detail)
        if hashlib.sha256(f"{anchor}|{payload}".encode()).hexdigest() != digest:
            return {"ok": False, "checked": checked, "error": "hash uyuşmazlığı"}
        prev = digest
        checked += 1
    return {"ok": True, "checked": checked, "truncated": truncated}
