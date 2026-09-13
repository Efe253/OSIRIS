"""Pipeline store() testleri — sahte psycopg imleci ile (DB gerektirmez)."""

import sys
import types

import pytest
from osiris_pipeline.pipeline import ProcessingPipeline


class FakeCursor:
    """fetchone kuyruklu sahte imleç; SAVEPOINT'leri yutar."""

    def __init__(self, fetchone_queue):
        self.queue = list(fetchone_queue)
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append(query)

    def fetchone(self):
        return self.queue.pop(0) if self.queue else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeConn:
    def __init__(self, cursor):
        self.cur = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True


def install_fake_psycopg(monkeypatch, cursor):
    fake = types.ModuleType("psycopg")
    fake.connect = lambda *a, **k: FakeConn(cursor)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", fake)


def base_result(**over):
    item = {
        "raw_content": "ham", "cleaned_content": "temiz", "url": "https://x",
        "title": "T", "language": "tr", "content_hash": "aa" * 32,
        "metadata": {}, "tags": [],
    }
    item.update(over.get("item", {}))
    return {
        "item": item,
        "entities": over.get("entities", [{"type": "email", "value": "a@b.co"}]),
        "topics": over.get("topics", []),
        "embedding": over.get("embedding"),
    }


def make_pipeline():
    p = ProcessingPipeline.__new__(ProcessingPipeline)
    p.database_url = "postgresql://localhost/db"
    p._embedding_usable = None
    return p


def test_store_inserts_item_and_entities(monkeypatch) -> None:
    cur = FakeCursor(fetchone_queue=[("item-1",), ("ent-1",)])
    install_fake_psycopg(monkeypatch, cur)
    p = make_pipeline()
    assert p.store(base_result()) == "item-1"
    assert any("INSERT INTO items" in s for s in cur.statements)
    assert any("INSERT INTO entities" in s for s in cur.statements)
    assert any("INSERT INTO item_entities" in s for s in cur.statements)


def test_store_dedup_returns_existing(monkeypatch) -> None:
    cur = FakeCursor(fetchone_queue=[None, ("eski-id",)])
    install_fake_psycopg(monkeypatch, cur)
    p = make_pipeline()
    assert p.store(base_result()) == "eski-id"


def test_store_with_embedding(monkeypatch) -> None:
    cur = FakeCursor(fetchone_queue=[("item-2",)])
    install_fake_psycopg(monkeypatch, cur)
    p = make_pipeline()
    assert p.store(base_result(embedding=[0.5, 0.6], entities=[])) == "item-2"
    assert p._embedding_usable is True
    assert any("SAVEPOINT" in s for s in cur.statements)


def test_store_embedding_mismatch_falls_back(monkeypatch) -> None:
    class BoomCursor(FakeCursor):
        def execute(self, query, params=None):
            super().execute(query, params)
            if "embedding" in query and "INSERT INTO items" in query:
                raise Exception("boyut uyumsuz")

    cur = BoomCursor(fetchone_queue=[("item-3",)])
    install_fake_psycopg(monkeypatch, cur)
    p = make_pipeline()
    assert p.store(base_result(embedding=[0.1], entities=[])) == "item-3"
    assert p._embedding_usable is False
    assert any("ROLLBACK TO SAVEPOINT" in s for s in cur.statements)


def test_store_requires_db_and_hash() -> None:
    p = ProcessingPipeline.__new__(ProcessingPipeline)
    p.database_url = None
    assert p.store({"item": {"content_hash": "x"}}) is None
    p.database_url = "postgresql://localhost/db"
    with pytest.raises(ValueError):
        p.store({"item": {}})


def test_store_skips_invalid_entities(monkeypatch) -> None:
    cur = FakeCursor(fetchone_queue=[("item-4",), ("ent-9",), ("ent-10",)])
    install_fake_psycopg(monkeypatch, cur)
    p = make_pipeline()
    entities = [
        {"type": "uzayli", "value": "x"},  # custom'a iner
        {"type": "email", "value": ""},  # atlanır
        {"type": "email", "value": "a@b.co"},
    ]
    assert p.store(base_result(entities=entities)) == "item-4"
