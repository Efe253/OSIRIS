"""Denetim zinciri (audit_logs) testleri — sahte DBAPI bağlantısıyla."""

from osiris.audit import append_audit, verify_chain


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.executed = []
        self.inserts = []

    def execute(self, query, params=None):
        self.executed.append(query)
        if query.strip().upper().startswith("INSERT"):
            self.inserts.append(params)

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeConn:
    def __init__(self, rows=None):
        self.cur = FakeCursor(rows)
        self.committed = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True


def test_append_audit_genesis() -> None:
    conn = FakeConn(rows=[])
    out = append_audit(conn, "api", "search", None, {"q": "x"})
    assert out["prev_hash"] == "GENESIS"
    assert len(out["hash"]) == 64
    assert conn.committed
    assert conn.cur.inserts[0][1] == "search"


def test_append_audit_chains_prev_hash() -> None:
    conn = FakeConn(rows=[("abc123",)])
    out = append_audit(conn, "api", "collect", "rss", {})
    assert out["prev_hash"] == "abc123"
    assert conn.cur.inserts[0][4] == "abc123"


def test_append_audit_rejects_bad_action() -> None:
    conn = FakeConn()
    try:
        append_audit(conn, None, "")
    except ValueError:
        pass
    else:
        raise AssertionError("boş action kabul edildi")
    assert not conn.cur.inserts


def test_verify_chain_ok_and_tamper() -> None:
    c1 = FakeConn()
    h1 = append_audit(c1, "u", "a1", "r", {"n": 1})["hash"]
    c2 = FakeConn(rows=[(h1,)])
    h2 = append_audit(c2, "u", "a2", None, None)["hash"]


    def row(user, action, resource, detail, prev, digest):
        return (user, action, resource, detail, prev, digest)

    good = FakeConn(rows=[
        row("u", "a1", "r", {"n": 1}, None, h1),
        row("u", "a2", None, {}, h1, h2),
    ])
    res = verify_chain(good)
    assert res == {"ok": True, "checked": 2}

    tampered = FakeConn(rows=[
        row("u", "a1", "r", {"n": 999}, None, h1),
        row("u", "a2", None, {}, h1, h2),
    ])
    res2 = verify_chain(tampered)
    assert res2["ok"] is False
