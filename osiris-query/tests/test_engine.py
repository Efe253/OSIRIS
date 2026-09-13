"""QueryEngine testleri — sahte bağlantı ile (DB gerektirmez)."""

import pytest
from osiris_query.engine import QueryEngine


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, *args):
        return self

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, *args):
        return FakeCursor(self.rows)


ROWS = [{"id": "1", "title": "T"}]


def engine(monkeypatch, rows=ROWS) -> QueryEngine:
    q = QueryEngine("postgresql://localhost/db")
    monkeypatch.setattr(QueryEngine, "_connect", lambda self: FakeConn(rows))
    return q


def test_fulltext_ok(monkeypatch) -> None:
    assert engine(monkeypatch).fulltext_search("saldırı") == ROWS


def test_fulltext_validation(monkeypatch) -> None:
    q = engine(monkeypatch)
    for bad in ["", "   ", "x" * 600]:
        with pytest.raises(ValueError):
            q.fulltext_search(bad)
    with pytest.raises(ValueError):
        q.fulltext_search("ok", limit=0)
    # büyük limit kelepçelenir (hata değil), string limit reddedilir
    assert q.fulltext_search("ok", limit=500) == ROWS
    with pytest.raises(ValueError):
        q.fulltext_search("ok", limit="yirmi")  # type: ignore[arg-type]


def test_semantic_ok_and_validation(monkeypatch) -> None:
    q = engine(monkeypatch)
    assert q.semantic_search([0.1, 0.2]) == ROWS
    for bad in [[], "degil", [0.1] * 5000, ["a"]]:
        with pytest.raises(ValueError):
            q.semantic_search(bad)


def test_entity_ok_and_validation(monkeypatch) -> None:
    q = engine(monkeypatch)
    assert q.entity_search("email", "a@b.co") == ROWS
    with pytest.raises(ValueError):
        q.entity_search("uzayli", "x")
    with pytest.raises(ValueError):
        q.entity_search("email", "")
    with pytest.raises(ValueError):
        q.entity_search("email", "x" * 600)


def test_requires_database_url() -> None:
    with pytest.raises(ValueError):
        QueryEngine("")


def test_non_string_inputs_rejected() -> None:
    import pytest
    from osiris_query.engine import QueryEngine

    with pytest.raises(ValueError):
        QueryEngine._validate_query(123)  # type: ignore[arg-type]
    q = QueryEngine("postgresql://localhost/db")
    with pytest.raises(ValueError):
        q.entity_search("email", 123)  # type: ignore[arg-type]
