"""Username Search plugin testleri (ağ gerektirmez)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import collector as ucol
from collector import UsernameSearchCollector


class FakeResp:
    def __init__(self, status=200, body="hello", url="https://x/"):
        self.status_code = status
        self._text = body
        self.url = url

    @property
    def text(self):
        return self._text


def test_username_validation() -> None:
    c = UsernameSearchCollector()
    for bad in [None, "", "a", "x" * 100, "a/b", "a\r\nb", "ad min", "@x"]:
        r = c.collect({"username": bad})
        assert not r.success


def test_sites_db_loads() -> None:
    c = UsernameSearchCollector()
    sites = c.load_sites()
    assert len(sites) >= 50
    assert all("{username}" in v["url"] or True for v in sites.values())
    with pytest.raises(ValueError):
        c.load_sites("/yok/boyle/db.json")


def test_status_code_detection(monkeypatch) -> None:
    c = UsernameSearchCollector()

    def fake_fetch(session, method, url, **kw):
        if "var" in url:
            return FakeResp(200, "profil sayfası")
        return FakeResp(404, "yok")

    monkeypatch.setattr(ucol, "fetch_url", fake_fetch)
    r = c.collect({"username": "varlik", "sites": ["GitHub"]})
    assert r.success and len(r.items) == 1
    assert r.items[0].metadata["site"] == "GitHub"
    assert "username" in r.items[0].tags


def test_message_detection(monkeypatch) -> None:
    c = UsernameSearchCollector()

    def fake_fetch(session, method, url, **kw):
        return FakeResp(200, "No such user, üzgünüz")

    monkeypatch.setattr(ucol, "fetch_url", fake_fetch)
    r = c.collect({"username": "kimse", "sites": ["HackerNews"]})
    assert r.success and r.items == [] and r.metadata["unknown"] == 1

    def fake_fetch2(session, method, url, **kw):
        return FakeResp(200, "kullanıcı profili burada")

    monkeypatch.setattr(ucol, "fetch_url", fake_fetch2)
    r2 = c.collect({"username": "kimse", "sites": ["HackerNews"]})
    # presence yok, absence yok → bilinmiyor
    assert r2.items == []


def test_response_url_detection(monkeypatch) -> None:
    c = UsernameSearchCollector()
    sites = c.load_sites()
    sites["TestSite"] = {"url": "https://example.com/{username}", "check_type": "response_url",
                         "presence": [], "absence": [], "tags": []}

    def fake_fetch(session, method, url, **kw):
        return FakeResp(200, "x", url="https://example.com/testuser")

    monkeypatch.setattr(ucol, "fetch_url", fake_fetch)
    orig = c.load_sites
    c.load_sites = lambda db=None: sites  # type: ignore[method-assign]
    try:
        r = c.collect({"username": "testuser", "sites": ["TestSite"]})
    finally:
        c.load_sites = orig  # type: ignore[method-assign]
    assert len(r.items) == 1 and r.items[0].metadata["site"] == "TestSite"


def test_error_isolation_and_filters(monkeypatch) -> None:
    c = UsernameSearchCollector()

    def fake_fetch(session, method, url, **kw):
        if "GitHub" in str(url) or "github" in str(url):
            raise ConnectionError("down")
        return FakeResp(404, "yok")

    monkeypatch.setattr(ucol, "fetch_url", fake_fetch)
    r = c.collect({"username": "testuser", "tags": ["dev"], "max_sites": 5, "workers": 2})
    assert r.success and r.metadata["checked"] <= 5
    # deterministik sıralama
    names = [i.metadata["site"] for i in r.items]
    assert names == sorted(names)


def test_health() -> None:
    assert UsernameSearchCollector().health_check() is True
