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
    assert c.delete("/auth/keys/12345678-1234-1234-1234-123456789abc", headers=oh).status_code == 200
    assert c.post("/auth/keys", json={"username": "x", "role": "kok"},
                  headers=oh).status_code == 400


class FakeDB:
    """_db() yerine geçen sahte veritabanı."""

    def __init__(self, fetchone=None, fetchall=None, rowcount=1):
        self._one = fetchone
        self._all = fetchall or []
        self.rowcount = rowcount
        self.statements = []

    def execute(self, q, p=None):
        self.statements.append(q)
        return self

    def fetchone(self):
        one = self._one() if callable(self._one) else self._one
        if isinstance(one, list):  # çağrı başına kuyruk
            return one.pop(0) if one else None
        return one

    def fetchall(self):
        return self._all() if callable(self._all) else self._all

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def cursor(self):
        return self

    def commit(self):
        pass


def patch_db(monkeypatch, **kwargs):
    monkeypatch.setattr(api_main, "_db", lambda: FakeDB(**kwargs))


def test_stats_and_recent(monkeypatch) -> None:
    c = make_client(monkeypatch)
    counts = [{"c": i} for i in range(7)] + [{"collected_at": "2026-01-01"}]
    patch_db(monkeypatch, fetchone=counts, fetchall=[{"id": "1", "title": "T"}])
    s = c.get("/stats", headers=auth()).json()
    assert s["items"] == 2 and s["latest_item_at"] == "2026-01-01"
    r = c.get("/items/recent?limit=5", headers=auth())
    assert r.status_code == 200 and r.json() == [{"id": "1", "title": "T"}]


def test_stats_db_error(monkeypatch) -> None:
    c = make_client(monkeypatch)

    def _boom():
        raise RuntimeError("db yok")

    monkeypatch.setattr(api_main, "_db", _boom)
    assert c.get("/stats", headers=auth()).status_code == 500


def test_sources_crud(monkeypatch) -> None:
    from osiris.plugin import BaseCollector

    class P(BaseCollector):
        id = "rss"
        name = "R"
        network_type = "rss"

    c = make_client(monkeypatch)
    api_main._collector.plugins["rss"] = P()
    patch_db(monkeypatch, fetchone={"id": "sid-1"})
    r = c.post("/sources",
               json={"name": "K", "plugin_id": "rss", "network_type": "rss",
                     "url": "https://x/rss"},
               headers=auth())
    assert r.status_code == 200 and r.json() == {"id": "sid-1"}
    bad = c.post("/sources", json={"name": "K", "plugin_id": "rss",
                                   "network_type": "uzay"},
                 headers=auth())
    assert bad.status_code == 400
    missing = c.post("/sources", json={"name": "K", "plugin_id": "yok"},
                     headers=auth())
    assert missing.status_code == 404


def test_sources_list_delete_collect(monkeypatch) -> None:
    c = make_client(monkeypatch)
    patch_db(monkeypatch, fetchone={"id": "s", "plugin_id": "rss", "url": "u",
                                    "metadata": {"config": {"feed_url": "u"}}},
               fetchall=[{"id": "s", "name": "N"}])
    assert c.get("/sources", headers=auth()).json() == [{"id": "s", "name": "N"}]
    sid = "12345678-1234-1234-1234-123456789abc"
    assert c.delete(f"/sources/{sid}", headers=auth()).json() == {"status": "deleted"}
    assert c.delete("/sources/yok", headers=auth()).status_code == 404


def test_collect_source_builds_config(monkeypatch) -> None:
    from osiris.plugin import BaseCollector, CollectionResult

    class P(BaseCollector):
        id = "rss"
        name = "R"
        network_type = "rss"

    c = make_client(monkeypatch)
    api_main._collector.plugins["rss"] = P()
    seen = {}

    def fake_run(pid, cfg):
        seen.update(cfg)
        return CollectionResult(items=[])

    api_main._collector.run_collection = fake_run  # type: ignore[method-assign]
    patch_db(monkeypatch, fetchone={"plugin_id": "rss", "url": "https://f/rss",
                                    "metadata": {"config": {}}})
    sid = "12345678-1234-1234-1234-123456789abc"
    r = c.post(f"/sources/{sid}/collect", headers=auth())
    assert r.status_code == 200
    assert seen["source_id"] == sid and seen["feed_url"] == "https://f/rss"


def test_saved_queries_crud_and_alert_test(monkeypatch) -> None:
    c = make_client(monkeypatch)
    patch_db(monkeypatch, fetchone={"id": "q-1"},
               fetchall=[{"id": "q-1", "name": "N", "query_text": "saldırı",
                          "alert_enabled": True}])
    r = c.post("/saved-queries",
               json={"name": "N", "query_text": "saldırı", "alert_enabled": True},
               headers=auth())
    assert r.json() == {"id": "q-1"}
    assert c.post("/saved-queries",
                  json={"name": "N", "query_text": "x", "query_type": "uzay"},
                  headers=auth()).status_code == 400
    assert len(c.get("/saved-queries", headers=auth()).json()) == 1
    t = c.post("/alerts/test", json={"text": "büyük saldırı oldu"},
               headers=auth())
    assert t.status_code == 200 and len(t.json()) == 1
    assert t.json()[0]["query_id"] == "q-1"
    assert c.delete("/saved-queries/12345678-1234-1234-1234-123456789abc", headers=auth()).json() == {"status": "deleted"}


def test_report_markdown(monkeypatch) -> None:
    c = make_client(monkeypatch)
    r = c.post("/reports/markdown",
               json={"title": "R", "scope": "S", "summary": "O",
                     "findings": [{"title": "B", "description": "D"}],
                     "sources": ["k"]},
               headers=auth())
    assert r.status_code == 200 and "# R" in r.json()["markdown"]


def test_plugins_include_schema(monkeypatch) -> None:
    from osiris.plugin import BaseCollector

    class P(BaseCollector):
        id = "rss"
        name = "R"
        network_type = "rss"

    c = make_client(monkeypatch)
    api_main._collector.plugins["rss"] = P()
    api_main._collector.plugins_dir = __import__("pathlib").Path("plugins")
    lst = c.get("/plugins", headers=auth()).json()
    rss = next(p for p in lst if p["id"] == "rss")
    assert "feed_url" in str(rss["config_schema"])


def test_items_detail_top_and_batch(monkeypatch) -> None:
    c = make_client(monkeypatch)
    item = {"id": "i1", "title": "T", "entities": []}
    patch_db(monkeypatch,
             fetchone=[item, [{"type": "email", "value": "a@b"}]],
             fetchall=[{"type": "email", "value": "a@b", "mentions": 5}])
    uid = "12345678-1234-1234-1234-123456789abc"
    r = c.get(f"/items/{uid}", headers=auth())
    assert r.status_code == 200 and r.json()["entities"][0]["value"] == "a@b"
    assert c.get("/items/bozuk", headers=auth()).status_code == 404
    t = c.get("/entities/top?limit=5", headers=auth())
    assert t.status_code == 200 and t.json()[0]["mentions"] == 5
    assert c.get("/entities/top?entity_type=uzayli", headers=auth()).status_code == 400


def test_collect_batch(monkeypatch) -> None:
    from osiris.plugin import BaseCollector, CollectedItem, CollectionResult

    class P(BaseCollector):
        id = "ok"
        name = "O"
        network_type = "www"

    c = make_client(monkeypatch)
    api_main._collector.plugins["ok"] = P()
    api_main._collector.run_collection = lambda pid, cfg: CollectionResult(  # type: ignore[method-assign]
        items=[CollectedItem(raw_content="x")])
    body = {"jobs": [{"plugin_id": "ok", "config": {}},
                     {"plugin_id": "yok", "config": {}}]}
    r = c.post("/collect/batch", json=body, headers=auth())
    assert r.status_code == 200
    data = r.json()
    assert (data["ok"], data["total"]) == (1, 2)
    assert c.post("/collect/batch", json={"jobs": []}, headers=auth()).status_code == 422
    many = {"jobs": [{"plugin_id": "ok", "config": {}}] * 11}
    assert c.post("/collect/batch", json=many, headers=auth()).status_code == 422


def test_sql_injection_attempts_are_inert(monkeypatch) -> None:
    """B608 incelemesi kanıtı: girdi yalnızca bağlı parametredir, yapı sabittir."""
    c = make_client(monkeypatch)
    seen: list[tuple[str, object]] = []

    class RecDB(FakeDB):
        def execute(self, q, p=None):
            seen.append((q, p))
            return self

    monkeypatch.setattr(api_main, "_db", lambda: RecDB(fetchall=[]))
    evil = "' OR '1'='1' -- ; DROP TABLE sources; /*"
    assert c.get("/sources", params={"q": evil}, headers=auth()).status_code == 200
    assert c.get("/sources", params={"plugin_id": "x'; DROP TABLE--"}, headers=auth()).status_code == 200
    # Yapı: tek SELECT, tek WHERE; girdi yalnızca parametrede
    for sql, _params in seen:
        assert sql.strip().upper().startswith("SELECT")
        assert sql.count(";") == 0
        assert "DROP TABLE" not in sql.upper()
    assert any(evil in str(p) for _, p in seen)  # girdi parametrede taşındı
    # UNION denemesi tablo dökemez (boş sonuç, hata yok)
    r = c.get("/entities/top", params={"entity_type": "email"}, headers=auth())
    assert r.status_code == 200


def test_disabled_source_conflict_and_audit_user(monkeypatch) -> None:
    c = make_client(monkeypatch)
    patch_db(monkeypatch, fetchone={"plugin_id": "rss", "url": "u",
                                    "enabled": False, "metadata": {}})
    r = c.post("/sources/12345678-1234-1234-1234-123456789abc/collect",
               headers=auth())
    assert r.status_code == 409

    calls = []
    monkeypatch.setattr(api_main, "_audit",
                        lambda *a, **k: calls.append((a, k)))
    patch_db(monkeypatch, fetchone={"c": 1},
               fetchall=[{"collected_at": None}])
    c.get("/stats", headers=auth())
    assert calls == []  # stats denetlenmez
    from osiris_api.auth import create_token

    viewer = create_token("gozlemci", "test-jwt-secret", role="viewer")["access_token"]
    monkeypatch.setattr(QueryEngine, "fulltext_search",
                        lambda self, q, limit=20: [])
    c.post("/search", json={"query": "x"},
           headers={"Authorization": f"Bearer {viewer}"})
    assert calls and calls[-1][1].get("user") == "gozlemci"
