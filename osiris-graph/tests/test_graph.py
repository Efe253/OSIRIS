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
