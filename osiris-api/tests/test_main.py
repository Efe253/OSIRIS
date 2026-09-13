"""API endpoint testleri (TestClient, gerçek DB/redis gerektirmez)."""

import os

os.environ.setdefault("OSIRIS_DATABASE_URL", "postgresql://localhost/db")
os.environ.setdefault("OSIRIS_REDIS_URL", "redis://localhost:6379/0")

import osiris_api.main as api_main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from osiris_api.main import app  # noqa: E402
from osiris_collector.manager import CollectorManager  # noqa: E402
from osiris_graph.engine import GraphEngine  # noqa: E402
from osiris_query.engine import QueryEngine  # noqa: E402


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(api_main, "API_KEY", "test-key")
    monkeypatch.setattr(api_main, "JWT_SECRET", "test-jwt-secret")
    monkeypatch.setattr(api_main, "_collector_loaded", True)
    api_main._collector = CollectorManager.__new__(CollectorManager)
    api_main._collector.plugins = {}
    api_main._collector.redis = None  # type: ignore[assignment]
    api_main._query = QueryEngine.__new__(QueryEngine)
    api_main._query.database_url = "postgresql://localhost/db"
    api_main._graph = GraphEngine()
    return TestClient(app, raise_server_exceptions=False)


def auth() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


def test_health_open(monkeypatch) -> None:
    c = make_client(monkeypatch)
    assert c.get("/health").json() == {"status": "ok", "service": "osiris-api"}


def test_auth_required(monkeypatch) -> None:
    c = make_client(monkeypatch)
    assert c.get("/plugins").status_code == 401
    assert c.get("/plugins", headers=auth()).status_code == 200


def test_bearer_works(monkeypatch) -> None:
    c = make_client(monkeypatch)
    from osiris_api.auth import create_token

    token = create_token("u", "test-jwt-secret")["access_token"]
    r = c.get("/plugins", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_collect_validation(monkeypatch) -> None:
    c = make_client(monkeypatch)
    assert c.post("/collect", json={"plugin_id": "yok", "config": {}},
                  headers=auth()).status_code == 404
    assert c.post("/collect", json={"plugin_id": "BAD ID!", "config": {}},
                  headers=auth()).status_code == 422
    # 413 için kayıtlı plugin gerekir (404 kontrolü önce gelir)
    api_main._collector.plugins["ok"] = object()
    big = {"plugin_id": "ok", "config": {"k": "x" * 25000}}
    assert c.post("/collect", json=big, headers=auth()).status_code == 413


def test_collect_success_with_stub(monkeypatch) -> None:
    from osiris.plugin import BaseCollector, CollectedItem, CollectionResult

    class Stub(BaseCollector):
        id = "stub"
        name = "S"
        network_type = "www"

        def collect(self, config=None):
            return CollectionResult(items=[CollectedItem(raw_content="x")])

    c = make_client(monkeypatch)
    api_main._collector.plugins["stub"] = Stub()
    api_main._collector.run_collection = lambda pid, cfg: CollectionResult(  # type: ignore[method-assign]
        items=[CollectedItem(raw_content="x")])
    r = c.post("/collect", json={"plugin_id": "stub", "config": {}},
               headers=auth())
    assert r.status_code == 200 and r.json()["items"] == 1


def test_collect_failure_maps_502(monkeypatch) -> None:
    from osiris.plugin import CollectionResult

    c = make_client(monkeypatch)
    api_main._collector.plugins["bad"] = object()
    api_main._collector.run_collection = lambda pid, cfg: CollectionResult(  # type: ignore[method-assign]
        items=[], success=False, error="patladi")
    r = c.post("/collect", json={"plugin_id": "bad", "config": {}},
               headers=auth())
    assert r.status_code == 502


def test_search_validation_and_ok(monkeypatch) -> None:
    c = make_client(monkeypatch)
    assert c.post("/search", json={"query": "", "limit": 5},
                  headers=auth()).status_code == 422
    monkeypatch.setattr(
        QueryEngine, "fulltext_search", lambda self, q, limit=20: [{"id": "1"}])
    r = c.post("/search", json={"query": "x", "limit": 5}, headers=auth())
    assert r.status_code == 200 and r.json() == [{"id": "1"}]


def test_search_db_error_maps_500(monkeypatch) -> None:
    c = make_client(monkeypatch)

    def _boom(self, q, limit=20):
        raise RuntimeError("db yok")

    monkeypatch.setattr(QueryEngine, "fulltext_search", _boom)
    assert c.post("/search", json={"query": "x"}, headers=auth()).status_code == 500


def test_entity_search(monkeypatch) -> None:
    c = make_client(monkeypatch)
    monkeypatch.setattr(
        QueryEngine, "entity_search",
        lambda self, t, v, limit=20: [{"id": "2"}])
    r = c.post("/search/entity",
               json={"entity_type": "email", "value": "a", "limit": 5},
               headers=auth())
    assert r.status_code == 200


def test_graph_roundtrip(monkeypatch) -> None:
    c = make_client(monkeypatch)
    r = c.post("/graph/relation",
               json={"source": "a", "target": "b", "relation_type": "knows"},
               headers=auth())
    assert r.status_code == 200
    g = c.get("/graph", headers=auth()).json()
    assert {n["id"] for n in g["nodes"]} == {"a", "b"}
    assert len(g["edges"]) == 1


def test_token_endpoint(monkeypatch) -> None:
    c = make_client(monkeypatch)
    r = c.post("/auth/token", json={"api_key": "test-key"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    assert c.post("/auth/token", json={"api_key": "nope"}).status_code == 401


def test_viewer_forbidden_on_write_endpoints(monkeypatch) -> None:
    from osiris_api.auth import create_token

    c = make_client(monkeypatch)
    viewer = create_token("v", "test-jwt-secret", role="viewer")["access_token"]
    vh = {"Authorization": f"Bearer {viewer}"}
    assert c.post("/collect", json={"plugin_id": "x", "config": {}},
                  headers=vh).status_code == 403
    assert c.post("/graph/relation",
                  json={"source": "a", "target": "b"},
                  headers=vh).status_code == 403
    # okuma serbest
    assert c.get("/plugins", headers=vh).status_code == 200
    analyst = create_token("a", "test-jwt-secret", role="analyst")["access_token"]
    ah = {"Authorization": f"Bearer {analyst}"}
    assert c.post("/graph/relation",
                  json={"source": "a", "target": "b"},
                  headers=ah).status_code == 200


def test_admin_only_key_management(monkeypatch) -> None:
    import sys
    import types

    import psycopg  # noqa: F401
    from osiris_api.auth import create_token

    c = make_client(monkeypatch)
    analyst = create_token("a", "test-jwt-secret", role="analyst")["access_token"]
    ah = {"Authorization": f"Bearer {analyst}"}
    assert c.get("/auth/keys", headers=ah).status_code == 403

    executed = []
    rows = [[("user-1",), ("key-1",)]]

    class FakeCur:
        def execute(self, q, p=None):
            executed.append(q)

        def fetchone(self):
            return rows[0].pop(0) if rows[0] else None

        def fetchall(self):
            return []

        @property
        def rowcount(self):
            return 1

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return FakeCur()

        def commit(self):
            pass

    fake = types.ModuleType("psycopg")
    fake.connect = lambda *a, **k: FakeConn()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    op = create_token("op", "test-jwt-secret", role="admin")["access_token"]
    oh = {"Authorization": f"Bearer {op}"}
    r = c.post("/auth/keys", json={"username": "ali", "role": "viewer"},
               headers=oh)
    assert r.status_code == 200
    assert r.json()["api_key"].startswith("osiris_")
    assert "api_key" not in str(c.get("/auth/keys", headers=oh).json())
    assert c.delete("/auth/keys/key-1", headers=oh).status_code == 200
    assert c.post("/auth/keys", json={"username": "x", "role": "kok"},
                  headers=oh).status_code == 400
