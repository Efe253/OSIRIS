"""CollectorManager testleri — sahte plugin ve mock redis ile."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from osiris.plugin import BaseCollector, CollectedItem, CollectionResult
from osiris_collector.manager import CollectorManager


class OkPlugin(BaseCollector):
    id = "ok"
    name = "OK"
    network_type = "www"

    def collect(self, config=None):
        return CollectionResult(
            items=[CollectedItem(raw_content="hello", title="T")], metadata={"n": 1}
        )


class FailPlugin(BaseCollector):
    id = "fail"
    name = "Fail"
    network_type = "www"

    def collect(self, config=None):
        return CollectionResult(items=[], success=False, error="boom")


class CrashPlugin(BaseCollector):
    id = "crash"
    name = "Crash"
    network_type = "www"

    def collect(self, config=None):
        raise RuntimeError("patladi")


def make_manager(**kwargs):
    mgr = CollectorManager.__new__(CollectorManager)
    mgr.plugins_dir = Path("plugins")
    mgr.plugins = {}
    mgr.redis = MagicMock()
    mgr.queue_name = "q"
    mgr.scheduler = MagicMock()
    mgr.database_url = None
    for k, v in kwargs.items():
        setattr(mgr, k, v)
    return mgr


def test_run_collection_success_queues_items() -> None:
    mgr = make_manager()
    mgr.plugins["ok"] = OkPlugin()
    result = mgr.run_collection("ok", {})
    assert result.success and len(result.items) == 1
    assert mgr.redis.rpush.call_count == 1


def test_run_collection_unknown_plugin() -> None:
    mgr = make_manager()
    with pytest.raises(KeyError):
        mgr.run_collection("yok", {})


def test_run_collection_bad_config() -> None:
    mgr = make_manager()
    mgr.plugins["ok"] = OkPlugin()
    result = mgr.run_collection("ok", "degil-dict")  # type: ignore[arg-type]
    assert not result.success


def test_run_collection_failure_and_crash() -> None:
    mgr = make_manager()
    mgr.plugins["fail"] = FailPlugin()
    assert not mgr.run_collection("fail", {}).success
    assert mgr.redis.rpush.call_count == 0
    mgr.plugins["crash"] = CrashPlugin()
    result = mgr.run_collection("crash", {})
    assert not result.success and "plugin hatası" in (result.error or "")


def test_run_collection_oversize_and_serialize_skip() -> None:
    mgr = make_manager()
    mgr.plugins["ok"] = OkPlugin()
    big = OkPlugin()

    def _big_collect(config=None):
        return CollectionResult(items=[CollectedItem(raw_content="x" * 600_000)])

    big.collect = _big_collect  # type: ignore[method-assign]
    mgr.plugins["big"] = big
    result = mgr.run_collection("big", {})
    assert result.success  # öğe atlanır ama görev başarılı
    assert mgr.redis.rpush.call_count == 0


def test_run_collection_redis_error() -> None:
    mgr = make_manager()
    import redis as redis_lib

    mgr.redis.rpush.side_effect = redis_lib.RedisError("down")
    mgr.plugins["ok"] = OkPlugin()
    result = mgr.run_collection("ok", {})
    assert not result.success and "kuyruk" in (result.error or "")


def test_load_plugins_missing_dir_and_bad_manifest(tmp_path: Path) -> None:
    mgr = make_manager(plugins_dir=tmp_path / "yok")
    assert mgr.load_plugins() == 0
    mgr2 = make_manager(plugins_dir=tmp_path)
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "manifest.json").write_text("{bozuk")
    (tmp_path / "noid").mkdir()
    (tmp_path / "noid" / "manifest.json").write_text('{"name": "x"}')
    (tmp_path / "nocol").mkdir()
    (tmp_path / "nocol" / "manifest.json").write_text('{"id": "nocol"}')
    assert mgr2.load_plugins() == 0


def test_load_plugins_real_dir_loads_all() -> None:
    mgr = make_manager()
    # Ortama göre 8-10 arası yüklenir (rss/dns-whois opsiyonel bağımlılıklı);
    # stdlib-only irc her zaman yüklenmeli
    assert 8 <= mgr.load_plugins() <= 10
    assert "irc" in mgr.plugins


def test_schedule_and_cron_validation() -> None:
    mgr = make_manager()
    mgr.schedule("ok", "*/15 * * * *", {})
    assert mgr.scheduler.add_job.called
    for bad in ["every minute", "* * *", "a b c d e", ""]:
        with pytest.raises(ValueError):
            mgr.schedule("ok", bad, {})


def test_record_health_noop_without_db() -> None:
    mgr = make_manager()
    # database_url yok → sessizce geçer, istisna yok
    mgr._record_health({"source_id": "x"}, CollectionResult(items=[]), 5)
    mgr.database_url = "postgresql://localhost/db"
    # DB yok → hata yutulur
    mgr._record_health({"source_id": "x"}, CollectionResult(items=[]), 5)
    mgr._record_health({}, CollectionResult(items=[]), 5)


def test_start_shutdown_delegate() -> None:
    mgr = make_manager()
    mgr.start()
    mgr.scheduler.start.assert_called_once()
    mgr.shutdown()
    mgr.scheduler.shutdown.assert_called_once()


def test_load_plugins_duplicate_and_exec_error(tmp_path) -> None:
    import textwrap

    mgr = make_manager(plugins_dir=tmp_path)
    d1 = tmp_path / "p1"
    d1.mkdir()
    (d1 / "manifest.json").write_text('{"id": "dup"}')
    (d1 / "collector.py").write_text(textwrap.dedent("""
        from osiris.plugin import BaseCollector, CollectionResult
        class C(BaseCollector):
            id = "dup"
            def collect(self, config=None):
                return CollectionResult(items=[])
    """))
    d2 = tmp_path / "p2"
    d2.mkdir()
    (d2 / "manifest.json").write_text('{"id": "dup"}')
    (d2 / "collector.py").write_text("raise RuntimeError('bozuk plugin')")
    d3 = tmp_path / "p3"
    d3.mkdir()
    (d3 / "manifest.json").write_text('{"id": "noclass"}')
    (d3 / "collector.py").write_text("X = 1")
    assert mgr.load_plugins() == 1
    assert list(mgr.plugins) == ["dup"]


def test_run_collection_unserializable_item() -> None:
    from unittest.mock import MagicMock

    from osiris.plugin import BaseCollector, CollectionResult

    class Weird(BaseCollector):
        id = "weird"
        name = "W"
        network_type = "www"

        def collect(self, config=None):
            item = MagicMock()
            item.model_dump.side_effect = TypeError("serilesmez")
            return CollectionResult(items=[item])

    mgr = make_manager()
    mgr.plugins["weird"] = Weird()
    result = mgr.run_collection("weird", {})
    assert result.success  # öğe atlanır, görev başarılı
    assert mgr.redis.rpush.call_count == 0


def test_record_health_with_fake_db(monkeypatch) -> None:
    import sys
    import types

    executed = []

    class FakeCur:
        def execute(self, q, p=None):
            executed.append(q)

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
    mgr = make_manager(database_url="postgresql://localhost/db")
    mgr._record_health({"source_id": "sid"}, CollectionResult(items=[]), 7)
    assert any("UPDATE sources" in q for q in executed)
    assert any("source_metrics" in q for q in executed)
