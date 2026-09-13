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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
    max_age=600,
)

DATABASE_URL = os.getenv("OSIRIS_DATABASE_URL", "postgresql://osiris:osiris@localhost:5432/osiris")
REDIS_URL = os.getenv("OSIRIS_REDIS_URL", "redis://localhost:6379/0")
API_KEY = os.getenv("OSIRIS_API_KEY", "")
if not API_KEY:
    logger.warning("OSIRIS_API_KEY tanımlı değil — API kimlik doğrulamasız çalışıyor (yalnızca güvenilir ağda kullanın)")

_collector = CollectorManager(redis_url=REDIS_URL)
_collector_loaded = False
_query = QueryEngine(DATABASE_URL)
_graph = GraphEngine()

_PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Geçersiz API anahtarı")


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


@app.get("/plugins", dependencies=[Depends(require_api_key)])
def list_plugins() -> list[dict[str, str]]:
    collector = get_collector()
    return [
        {"id": pid, "name": p.name, "network_type": p.network_type}
        for pid, p in collector.plugins.items()
    ]


@app.post("/collect", dependencies=[Depends(require_api_key)])
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


@app.post("/search", dependencies=[Depends(require_api_key)])
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


@app.post("/search/entity", dependencies=[Depends(require_api_key)])
def entity_search(req: EntitySearchRequest) -> list[dict[str, Any]]:
    try:
        return _query.entity_search(req.entity_type, req.value, req.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Varlık araması hatası")
        raise HTTPException(status_code=500, detail="Arama başarısız") from exc


@app.get("/graph", dependencies=[Depends(require_api_key)])
def graph() -> dict[str, Any]:
    import json

    try:
        return json.loads(_graph.to_json())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="Graf okunamadı") from exc


@app.post("/graph/relation", dependencies=[Depends(require_api_key)])
def graph_add(req: GraphAddRequest) -> dict[str, str]:
    _graph.add_entity(req.source)
    _graph.add_entity(req.target)
    _graph.add_relation(req.source, req.target, req.relation_type)
    return {"status": "ok"}


def run() -> None:
    import uvicorn

    uvicorn.run("osiris_api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
