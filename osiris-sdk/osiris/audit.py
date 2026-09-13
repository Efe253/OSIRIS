"""Denetim logları — append-only, hash zincirli (doküman §10.4).

`audit_logs` tablosuna yazar; her kayıt bir öncekinin SHA-256 özetini içerir.
psycopg bağımlılığı almamak için DBAPI-uyumlu bir bağlantı (duck-typing)
kabul eder: yalnızca ``.cursor()`` + context manager protokolü gerekir.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol


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
    )


def append_audit(conn: _Connection, user_id: str | None, action: str,
                 resource: str | None = None,
                 detail: dict[str, Any] | None = None) -> dict[str, str]:
    """Zincire yeni bir denetim kaydı ekler. ``{'prev_hash', 'hash'}`` döner."""
    if not action or len(action) > 200:
        raise ValueError("action 1-200 karakter olmalı")
    if resource is not None and len(resource) > 500:
        raise ValueError("resource çok uzun")
    payload = _canonical(user_id, action, resource, detail)

    cur = conn.cursor()
    try:
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
                (user_id or "")[:200],
                action,
                (resource or "")[:500],
                json.dumps(detail or {}, ensure_ascii=False),
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
    """Son N kaydın zincir bütünlüğünü doğrular."""
    limit = max(1, min(int(limit), 100_000))
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT user_id, action, resource, detail, prev_hash, hash"
            " FROM audit_logs ORDER BY id ASC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    finally:
        close = getattr(cur, "close", None)
        if callable(close):
            close()
    prev = "GENESIS"
    checked = 0
    for user_id, action, resource, detail, prev_hash, digest in rows:
        expected_prev = None if prev == "GENESIS" else prev
        if prev_hash != expected_prev:
            return {"ok": False, "checked": checked, "error": "prev_hash uyuşmazlığı"}
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except ValueError:
                detail = {}
        payload = _canonical(user_id, action, resource, detail)
        if hashlib.sha256(f"{prev}|{payload}".encode()).hexdigest() != digest:
            return {"ok": False, "checked": checked, "error": "hash uyuşmazlığı"}
        prev = digest
        checked += 1
    return {"ok": True, "checked": checked}
