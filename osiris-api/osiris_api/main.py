"""OSIRIS REST API — FastAPI uygulaması.

Bkz. doküman §5.8.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from osiris_collector.manager import CollectorManager
from osiris_graph.engine import GraphEngine
from osiris_query.engine import QueryEngine

app = FastAPI(title="OSIRIS API", version="0.1.0")

DATABASE_URL = os.getenv("OSIRIS_DATABASE_URL", "postgresql://osiris:osiris@localhost:5432/osiris")
REDIS_URL = os.getenv("OSIRIS_REDIS_URL", "redis://localhost:6379/0")

_collector = CollectorManager(redis_url=REDIS_URL)
_query = QueryEngine(DATABASE_URL)
_graph = GraphEngine()


class CollectRequest(BaseModel):
    plugin_id: str
    config: dict[str, Any] = {}


class SearchRequest(BaseModel):
    query: str
    limit: int = 20


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "osiris-api"}


@app.get("/plugins")
def list_plugins() -> list[dict[str, str]]:
    _collector.load_plugins()
    return [
        {"id": pid, "name": p.name, "network_type": p.network_type}
        for pid, p in _collector.plugins.items()
    ]


@app.post("/collect")
def collect(req: CollectRequest) -> dict[str, Any]:
    _collector.load_plugins()
    result = _collector.run_collection(req.plugin_id, req.config)
    if not result.success:
        raise HTTPException(status_code=502, detail=result.error)
    return {"items": len(result.items), "metadata": result.metadata}


@app.post("/search")
def search(req: SearchRequest) -> list[dict[str, Any]]:
    try:
        return _query.fulltext_search(req.query, req.limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/graph")
def graph() -> dict[str, Any]:
    return {"nodes": [], "edges": []}


def run() -> None:
    import uvicorn

    uvicorn.run("osiris_api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
