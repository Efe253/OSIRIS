"""OSIRIS REST API — FastAPI uygulaması.

Bkz. doküman §5.8.
"""

from __future__ import annotations

import json
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
def list_plugins() -> list[dict[str, Any]]:
    collector = get_collector()
    out = []
    for pid, p in collector.plugins.items():
        try:
            manifest = collector.get_manifest(pid)
        except (KeyError, ValueError):
            manifest = {}
        out.append({
            "id": pid,
            "name": p.name,
            "network_type": p.network_type,
            "description": manifest.get("description", ""),
            "config_schema": manifest.get("config_schema", {}),
            "schedule_default": manifest.get("schedule_default", ""),
        })
    return out


def _db():
    """dict satırlı kısa ömürlü DB bağlantısı (testlerde yamalanabilir)."""
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(DATABASE_URL, connect_timeout=5, row_factory=dict_row)


@app.get("/stats", dependencies=[Depends(require_viewer)])
def stats() -> dict[str, Any]:
    """Panel için sayaçlar: kaynak/öğe/varlık/kenar/sorgu."""
    try:
        with _db() as conn:
            counts = {}
            for key, table, extra in [
                ("sources", "sources", ""),
                ("sources_enabled", "sources", "WHERE enabled"),
                ("items", "items", ""),
                ("entities", "entities", ""),
                ("edges", "graph_edges", ""),
                ("saved_queries", "saved_queries", ""),
                ("alerts", "saved_queries", "WHERE alert_enabled"),
            ]:
                counts[key] = conn.execute(
                    f"SELECT count(*) AS c FROM {table} {extra}".rstrip()
                ).fetchone()["c"]
            latest = conn.execute(
                "SELECT collected_at FROM items ORDER BY collected_at DESC LIMIT 1"
            ).fetchone()
        counts["latest_item_at"] = latest["collected_at"] if latest else None
        return counts
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="İstatistik okunamadı") from exc


@app.get("/items/recent", dependencies=[Depends(require_viewer)])
def recent_items(limit: int = 20) -> list[dict[str, Any]]:
    """En son toplanan öğeler (panel akışı)."""
    limit = max(1, min(int(limit), 50))
    try:
        with _db() as conn:
            rows = conn.execute(
                """
                SELECT id::text AS id, title, url, language,
                       LEFT(cleaned_content, 500) AS snippet,
                       collected_at, tags
                FROM items ORDER BY collected_at DESC LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Öğeler okunamadı") from exc


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


class SourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    plugin_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    url: str = Field(default="", max_length=2048)
    network_type: str = Field(default="www", max_length=32)
    schedule: str = Field(default="", max_length=100)
    priority: int = Field(default=5, ge=1, le=10)
    enabled: bool = True
    tags: list[str] = Field(default_factory=list, max_length=20)
    config: dict[str, Any] = Field(default_factory=dict, max_length=50)


_VALID_NETWORKS = {"www", "tor", "i2p", "p2p", "freenet", "zeronet", "irc",
                   "matrix", "rss", "api", "blockchain", "sdr", "custom"}


@app.get("/sources", dependencies=[Depends(require_viewer)])
def list_sources() -> list[dict[str, Any]]:
    try:
        with _db() as conn:
            rows = conn.execute(
                """
                SELECT id::text AS id, name, url, network_type::text AS network_type,
                       plugin_id, schedule, priority, enabled, tags,
                       last_crawled_at, last_success_at, failure_count, avg_response_ms
                FROM sources ORDER BY name LIMIT 500
                """
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Kaynaklar okunamadı") from exc


@app.post("/sources", dependencies=[Depends(require_analyst)])
def create_source(req: SourceRequest) -> dict[str, str]:
    if req.network_type not in _VALID_NETWORKS:
        raise HTTPException(status_code=400, detail="Geçersiz network_type")
    if req.plugin_id not in get_collector().plugins:
        raise HTTPException(status_code=404, detail="Plugin bulunamadı")
    try:
        with _db() as conn:
            row = conn.execute(
                """
                INSERT INTO sources
                    (name, url, network_type, plugin_id, schedule, priority,
                     enabled, tags, metadata)
                VALUES (%s, NULLIF(%s,''), %s::network_type, %s,
                        NULLIF(%s,''), %s, %s, %s, %s::jsonb)
                RETURNING id::text AS id
                """,
                (req.name, req.url, req.network_type, req.plugin_id,
                 req.schedule, req.priority, req.enabled,
                 [str(t)[:100] for t in req.tags[:20]],
                 json.dumps({"config": req.config}, ensure_ascii=False)),
            ).fetchone()
            conn.commit()
        _audit("source.create", req.name, {"plugin": req.plugin_id})
        return {"id": row["id"]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Kaynak oluşturulamadı") from exc


@app.delete("/sources/{source_id}", dependencies=[Depends(require_analyst)])
def delete_source(source_id: str) -> dict[str, str]:
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sources WHERE id::text = %s", (source_id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Kaynak bulunamadı")
            conn.commit()
        _audit("source.delete", None, {"id": source_id})
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Kaynak silinemedi") from exc


@app.post("/sources/{source_id}/collect", dependencies=[Depends(require_analyst)])
def collect_source(source_id: str) -> dict[str, Any]:
    """Kayıtlı kaynağı tek seferlik çalıştırır (sağlık takibi dahil)."""
    try:
        with _db() as conn:
            row = conn.execute(
                """
                SELECT plugin_id, url, metadata FROM sources WHERE id::text = %s
                """,
                (source_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Kaynak bulunamadı")
        row = dict(row)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Kaynak okunamadı") from exc
    meta = row.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except ValueError:
            meta = {}
    task_config: dict[str, Any] = dict(meta.get("config") or {})
    task_config["source_id"] = source_id
    if row.get("url"):
        for key in ("url", "feed_url", "endpoint"):
            task_config.setdefault(key, row["url"])
    collector = get_collector()
    if row["plugin_id"] not in collector.plugins:
        raise HTTPException(status_code=404, detail="Plugin bulunamadı")
    try:
        result = collector.run_collection(row["plugin_id"], task_config)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error)
    _audit("source.collect", row["plugin_id"], {"id": source_id, "items": len(result.items)})
    return {"items": len(result.items), "metadata": result.metadata}


class SavedQueryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    query_text: str = Field(min_length=1, max_length=500)
    query_type: str = Field(default="fts", max_length=32)
    alert_enabled: bool = False


_VALID_QUERY_TYPES = {"fts", "semantic", "regex", "entity", "graph"}


@app.get("/saved-queries", dependencies=[Depends(require_viewer)])
def list_saved_queries() -> list[dict[str, Any]]:
    try:
        with _db() as conn:
            rows = conn.execute(
                """
                SELECT id::text AS id, name, query_text,
                       query_type::text AS query_type, alert_enabled, last_triggered_at
                FROM saved_queries ORDER BY name LIMIT 500
                """
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Sorgular okunamadı") from exc


@app.post("/saved-queries", dependencies=[Depends(require_analyst)])
def create_saved_query(req: SavedQueryRequest) -> dict[str, str]:
    if req.query_type not in _VALID_QUERY_TYPES:
        raise HTTPException(status_code=400, detail="Geçersiz query_type")
    try:
        with _db() as conn:
            row = conn.execute(
                """
                INSERT INTO saved_queries (name, query_text, query_type, alert_enabled)
                VALUES (%s, %s, %s::query_type, %s)
                RETURNING id::text AS id
                """,
                (req.name, req.query_text, req.query_type, req.alert_enabled),
            ).fetchone()
            conn.commit()
        return {"id": row["id"]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Sorgu oluşturulamadı") from exc


@app.delete("/saved-queries/{query_id}", dependencies=[Depends(require_analyst)])
def delete_saved_query(query_id: str) -> dict[str, str]:
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM saved_queries WHERE id::text = %s", (query_id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Sorgu bulunamadı")
            conn.commit()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Sorgu silinemedi") from exc


class AlertTestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    title: str = Field(default="", max_length=2000)


@app.post("/alerts/test", dependencies=[Depends(require_analyst)])
def test_alerts(req: AlertTestRequest) -> list[dict[str, Any]]:
    """Ham metni kayıtlı uyarı sorgularıyla eşleştirir (kayıt oluşturmaz)."""
    from osiris_alert.manager import AlertManager

    try:
        with _db() as conn:
            queries = conn.execute(
                """
                SELECT id::text AS id, name, query_text, alert_enabled
                FROM saved_queries WHERE alert_enabled LIMIT 100
                """
            ).fetchall()
        manager = AlertManager(redis_url=None)
        return manager.check_item(
            {"cleaned_content": req.text, "title": req.title},
            [dict(q) for q in queries],
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Eşleşme başarısız") from exc


class MarkdownReportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    scope: str = Field(default="", max_length=1000)
    summary: str = Field(default="", max_length=20_000)
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    sources: list[str] = Field(default_factory=list, max_length=500)


@app.post("/reports/markdown", dependencies=[Depends(require_analyst)])
def report_markdown(req: MarkdownReportRequest) -> dict[str, str]:
    """Markdown rapor üretir (gövdeyle döner, diske yazmaz)."""
    from osiris_report.generator import ReportGenerator

    try:
        content = ReportGenerator().generate_markdown(
            req.title, req.scope, req.summary, req.findings, req.sources)
        return {"markdown": content}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Rapor üretilemedi") from exc


def run() -> None:
    import uvicorn

    uvicorn.run("osiris_api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
