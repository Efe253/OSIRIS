"""Graph Engine testleri."""

from osiris_graph.engine import GraphEngine


def test_add_relation_and_neighbors() -> None:
    g = GraphEngine()
    g.add_entity("alice", type="person")
    g.add_entity("bob", type="person")
    g.add_relation("alice", "bob", "knows", 2.0)
    assert g.neighbors("alice") == ["bob"]


def test_centrality() -> None:
    g = GraphEngine()
    g.add_relation("a", "b")
    g.add_relation("a", "c")
    g.add_relation("a", "d")
    cent = g.centrality()
    assert cent["a"] == 1.0


def test_communities() -> None:
    g = GraphEngine()
    for pair in [("a", "b"), ("b", "c"), ("x", "y")]:
        g.add_relation(*pair)
    assert len(g.communities()) >= 1


def test_validation_and_limits() -> None:
    import pytest
    from osiris_graph.engine import GraphEngine

    g = GraphEngine(max_nodes=2)
    with pytest.raises(ValueError):
        g.add_entity("")
    with pytest.raises(ValueError):
        g.add_entity("x" * 600)
    with pytest.raises(ValueError):
        g.add_relation("a", "b", weight="agir")  # type: ignore[arg-type]
    g.add_entity("a")
    g.add_entity("b")
    with pytest.raises(OverflowError):
        g.add_entity("c")
    with pytest.raises(OverflowError):
        g.add_relation("a", "z")
    g.add_relation("a", "a")  # self-loop yoksayılır
    assert g.neighbors("a") == []


def test_export_and_json(tmp_path) -> None:
    import json

    from osiris_graph.engine import GraphEngine

    g = GraphEngine()
    assert g.centrality() == {}
    assert g.communities() == []
    g.add_entity("a", type="person")
    assert g.communities() == [["a"]]
    g.add_relation("a", "b", "knows", 2.0)
    data = json.loads(g.to_json())
    assert len(data["nodes"]) == 2 and len(data["edges"]) == 1
    g.export_graphml(str(tmp_path / "g.graphml"))
    g.export_gexf(str(tmp_path / "g.gexf"))
    assert (tmp_path / "g.graphml").exists()


def test_persistence_roundtrip(monkeypatch) -> None:
    import sys
    import types

    from osiris_graph.engine import GraphEngine

    stored = []
    rows = [[("a", "b", "knows", 2.0), ("b", "c", "related", 1.0)]]

    class FakeCur:
        def execute(self, q, p=None):
            if q.strip().upper().startswith("INSERT"):
                stored.append(p)

        def executemany(self, q, seq):
            stored.extend(seq)

        def fetchall(self):
            return rows[0]

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

    g = GraphEngine(database_url="postgresql://localhost/db")
    assert GraphEngine().save_to_db() == 0  # urlsiz
    assert GraphEngine().load_from_db() == 0
    g.add_relation("a", "b", "knows", 2.0)
    assert g.save_to_db() == 1
    assert stored[0][:3] == ("a", "b", "knows")

    g2 = GraphEngine(database_url="postgresql://localhost/db")
    assert g2.load_from_db() == 2
    assert g2.neighbors("b") == ["a", "c"]
