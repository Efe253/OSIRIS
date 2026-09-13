"""OSIRIS REST API — FastAPI uygulaması.

Bkz. doküman §5.8.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from osiris_collector.manager import CollectorManager
from osiris_graph.engine import GraphEngine
from osiris_query.engine import QueryEngine
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="OSIRIS API", version="0.1.0", docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("OSIRIS_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    max_age=600,
)

DATABASE_URL = os.getenv("OSIRIS_DATABASE_URL", "postgresql://osiris:osiris@localhost:5432/osiris")
REDIS_URL = os.getenv("OSIRIS_REDIS_URL", "redis://localhost:6379/0")
API_KEY = os.getenv("OSIRIS_API_KEY", "")
JWT_SECRET = os.getenv("OSIRIS_JWT_SECRET", "") or API_KEY
if not API_KEY:
    logger.warning("OSIRIS_API_KEY tanımlı değil — API kimlik doğrulamasız çalışıyor (yalnızca güvenilir ağda kullanın)")

_collector = CollectorManager(redis_url=REDIS_URL)
_collector_loaded = False
_query = QueryEngine(DATABASE_URL)
_graph = GraphEngine(database_url=DATABASE_URL)
_graph_loaded = False

_PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def get_graph() -> GraphEngine:
    """Grafı ilk kullanımda DB'den besler (best-effort kalıcılık)."""
    global _graph_loaded
    if not _graph_loaded:
        _graph_loaded = True
        try:
            _graph.load_from_db()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Graf yüklenemedi: %s", exc)
    return _graph


def _lookup_db_key(raw_key: str) -> dict[str, str] | None:
    """Veritabanındaki kullanıcı anahtarını çözer (hash karşılaştırma)."""
    from osiris_api.auth import hash_api_key

    try:
        import psycopg

        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.username, u.role::text FROM api_keys k
                    JOIN users u ON u.id = k.user_id
                    WHERE k.key_hash = %s AND NOT k.revoked
                    """,
                    (hash_api_key(raw_key),),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = %s",
                    (hash_api_key(raw_key),),
                )
                conn.commit()
                return {"user": row[0], "role": row[1]}
    except Exception as exc:  # noqa: BLE001
        logger.debug("Anahtar araması atlandı: %s", exc)
        return None


def _check_api_key(provided: str | None) -> bool:
    if not API_KEY or not provided:
        return False
    import hmac as _hmac

    return _hmac.compare_digest(provided, API_KEY)


def resolve_identity(
    x_api_key: str | None = None,
    authorization: str | None = None,
) -> dict[str, str] | None:
    """Kimliği çözer: operatör anahtarı → DB anahtarı → Bearer JWT."""
    if _check_api_key(x_api_key):
        return {"user": "operator", "role": "admin"}
    if authorization and authorization.lower().startswith("bearer "):
        from osiris_api.auth import verify_token_with_role

        try:
            sub, role = verify_token_with_role(authorization[7:].strip(), JWT_SECRET)
            return {"user": sub, "role": role}
        except ValueError:
            pass
    if x_api_key:
        ident = _lookup_db_key(x_api_key)
        if ident is not None:
            return ident
    return None


def _require_role(
    minimum: str,
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    from osiris_api.auth import role_satisfies

    if not API_KEY:
        return {"user": "anonymous", "role": "admin"}  # açık mod
    ident = resolve_identity(x_api_key, authorization)
    if ident is None:
        raise HTTPException(status_code=401, detail="Geçersiz kimlik bilgisi")
    if not role_satisfies(ident["role"], minimum):
        raise HTTPException(status_code=403, detail="Yetki yetersiz")
    return ident


def require_viewer(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    return _require_role("viewer", x_api_key, authorization)


def require_analyst(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    return _require_role("analyst", x_api_key, authorization)


def require_admin(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    return _require_role("admin", x_api_key, authorization)


def require_auth(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> None:
    """Geriye uyumlu: herhangi bir geçerli kimlik (viewer eşiği)."""
    require_viewer(x_api_key, authorization)


# Geriye uyumluluk: eski bağımlılık adı
require_api_key = require_auth


def get_collector() -> CollectorManager:
    global _collector_loaded
    if not _collector_loaded:
        _collector.load_plugins()
        _collector_loaded = True
    return _collector


def _audit(action: str, resource: str | None = None,
           detail: dict[str, Any] | None = None) -> None:
    """Best-effort denetim kaydı (doküman §10.4). Asla isteği bozmaz."""
    try:
        import psycopg
        from osiris.audit import append_audit

        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            append_audit(conn, "api", action, resource, detail)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Denetim kaydı atlandı: %s", exc)


class CollectRequest(BaseModel):
    plugin_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    config: dict[str, Any] = Field(default_factory=dict, max_length=50)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class EntitySearchRequest(BaseModel):
    entity_type: str = Field(min_length=1, max_length=32)
    value: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class GraphAddRequest(BaseModel):
    source: str = Field(min_length=1, max_length=500)
    target: str = Field(min_length=1, max_length=500)
    relation_type: str = Field(default="related", max_length=100)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "osiris-api"}


class TokenRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=500)
    role: str = Field(default="viewer", max_length=32)


@app.post("/auth/token")
def issue_token(req: TokenRequest) -> dict[str, object]:
    """Operatör anahtarı karşılığında kısa ömürlü JWT üretir (1 saat)."""
    if not API_KEY or not JWT_SECRET:
        raise HTTPException(status_code=404, detail="Jeton üretimi kapalı")
    if not _check_api_key(req.api_key):
        raise HTTPException(status_code=401, detail="Geçersiz kimlik bilgisi")
    from osiris_api.auth import ROLES, create_token

    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail="Geçersiz rol")
    token = create_token("api-client", JWT_SECRET, role=req.role)
    _audit("auth.token", None, {"role": req.role})
    return token


class ApiKeyRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    role: str = Field(default="viewer", max_length=32)
    name: str = Field(default="", max_length=200)


@app.post("/auth/keys", dependencies=[Depends(require_admin)])
def create_api_key(req: ApiKeyRequest) -> dict[str, str]:
    """Kullanıcıya API anahtarı üretir (ham değer BİR KEZ döner)."""
    import secrets

    from osiris_api.auth import ROLES, hash_api_key

    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail="Geçersiz rol")
    raw_key = f"osiris_{secrets.token_urlsafe(32)}"
    try:
        import psycopg

        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, role)
                    VALUES (%s, %s)
                    ON CONFLICT (username)
                    DO UPDATE SET role = EXCLUDED.role
                    RETURNING id::text
                    """,
                    (req.username, req.role),
                )
                user_id = cur.fetchone()[0]
                cur.execute(
                    """
                    INSERT INTO api_keys (user_id, key_hash, key_prefix, name)
                    VALUES (%s::uuid, %s, %s, %s)
                    RETURNING id::text
                    """,
                    (user_id, hash_api_key(raw_key), raw_key[:8], req.name[:200]),
                )
                key_id = cur.fetchone()[0]
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Anahtar üretilemedi")
        raise HTTPException(status_code=500, detail="Anahtar üretilemedi") from exc
    _audit("auth.key.create", req.username, {"role": req.role, "key_id": key_id})
    return {"id": key_id, "api_key": raw_key, "role": req.role}


@app.get("/auth/keys", dependencies=[Depends(require_admin)])
def list_api_keys() -> list[dict[str, Any]]:
    """Anahtarları listeler (ham değerler ASLA dönülmez)."""
    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(DATABASE_URL, connect_timeout=5,
                             row_factory=dict_row) as conn:
            rows = conn.execute(
                """
                SELECT k.id::text AS id, u.username, u.role::text AS role,
                       k.key_prefix, k.name, k.revoked, k.created_at, k.last_used_at
                FROM api_keys k JOIN users u ON u.id = k.user_id
                ORDER BY k.created_at DESC LIMIT 200
                """
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Liste okunamadı") from exc


@app.delete("/auth/keys/{key_id}", dependencies=[Depends(require_admin)])
def revoke_api_key(key_id: str) -> dict[str, str]:
    """Anahtarı iptal eder (silmez — denetim izi kalır)."""
    try:
        import psycopg

        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE api_keys SET revoked = TRUE WHERE id::text = %s",
                    (key_id,),
                )
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Anahtar bulunamadı")
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="İptal başarısız") from exc
    _audit("auth.key.revoke", None, {"key_id": key_id})
    return {"status": "revoked"}


@app.get("/plugins", dependencies=[Depends(require_viewer)])
def list_plugins() -> list[dict[str, str]]:
    collector = get_collector()
    return [
        {"id": pid, "name": p.name, "network_type": p.network_type}
        for pid, p in collector.plugins.items()
    ]


@app.post("/collect", dependencies=[Depends(require_analyst)])
def collect(req: CollectRequest) -> dict[str, Any]:
    collector = get_collector()
    if req.plugin_id not in collector.plugins:
        raise HTTPException(status_code=404, detail="Plugin bulunamadı")
    if len(str(req.config)) > 20_000:
        raise HTTPException(status_code=413, detail="config çok büyük")
    try:
        result = collector.run_collection(req.plugin_id, req.config)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not result.success:
        _audit("collect.failed", req.plugin_id, {"error": result.error})
        raise HTTPException(status_code=502, detail=result.error)
    _audit("collect", req.plugin_id, {"items": len(result.items)})
    return {"items": len(result.items), "metadata": result.metadata}


@app.post("/search", dependencies=[Depends(require_viewer)])
def search(req: SearchRequest) -> list[dict[str, Any]]:
    try:
        rows = _query.fulltext_search(req.query, req.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Arama hatası")
        raise HTTPException(status_code=500, detail="Arama başarısız") from exc
    _audit("search", None, {"query": req.query[:200], "hits": len(rows)})
    return rows


@app.post("/search/entity", dependencies=[Depends(require_viewer)])
def entity_search(req: EntitySearchRequest) -> list[dict[str, Any]]:
    try:
        return _query.entity_search(req.entity_type, req.value, req.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Varlık araması hatası")
        raise HTTPException(status_code=500, detail="Arama başarısız") from exc


@app.get("/graph", dependencies=[Depends(require_viewer)])
def graph() -> dict[str, Any]:
    import json

    try:
        return json.loads(get_graph().to_json())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Graf okunamadı") from exc


@app.post("/graph/relation", dependencies=[Depends(require_analyst)])
def graph_add(req: GraphAddRequest) -> dict[str, str]:
    g = get_graph()
    g.add_entity(req.source)
    g.add_entity(req.target)
    g.add_relation(req.source, req.target, req.relation_type)
    try:
        g.save_to_db()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Graf persist atlandı: %s", exc)
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    uvicorn.run("osiris_api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
