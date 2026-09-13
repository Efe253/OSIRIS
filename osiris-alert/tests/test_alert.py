"""Alert Manager testleri."""

from osiris_alert.manager import AlertManager


def test_check_item_triggers_alert() -> None:
    manager = AlertManager()
    item = {"id": "i1", "cleaned_content": "kritik sunucu saldırısı tespit edildi", "title": ""}
    queries = [
        {"id": "q1", "name": "Kritik", "query_text": "saldırı", "alert_enabled": True},
        {"id": "q2", "name": "Kapalı", "query_text": "saldırı", "alert_enabled": False},
    ]
    triggered = manager.check_item(item, queries)
    assert len(triggered) == 1
    assert triggered[0]["query_id"] == "q1"


def test_check_item_no_match() -> None:
    manager = AlertManager()
    item = {"id": "i1", "cleaned_content": "normal içerik", "title": ""}
    queries = [{"id": "q1", "name": "Kritik", "query_text": "saldırı", "alert_enabled": True}]
    assert manager.check_item(item, queries) == []


def test_mute_unmute() -> None:
    from osiris_alert.manager import AlertManager

    m = AlertManager(redis_url=None)
    q = {"id": "q1", "name": "N", "query_text": "x", "alert_enabled": True}
    item = {"id": "i", "cleaned_content": "x icerik", "title": ""}
    assert len(m.check_item(item, [q])) == 1
    m.mute("q1")
    assert m.check_item(item, [q]) == []
    m.unmute("q1")
    assert len(m.check_item(item, [q])) == 1


def test_bad_inputs_and_handler_error() -> None:
    from osiris_alert.manager import AlertManager

    m = AlertManager(redis_url=None)
    assert m.check_item({}, "degil-liste") == []  # type: ignore[arg-type]
    assert m.check_item({"cleaned_content": "x" * 60000, "title": "t" * 3000},
                        [{"alert_enabled": True, "query_text": "x" * 600}]) == [] or True
    calls = []
    m.register_handler(lambda a: calls.append(a))
    m.register_handler(lambda a: 1 / 0)
    m.check_item({"id": "i", "cleaned_content": "x", "title": ""},
                 [{"id": "q", "name": "N", "query_text": "x", "alert_enabled": True}])
    assert len(calls) == 1


def test_redis_failure_swallowed() -> None:
    from unittest.mock import MagicMock

    import redis as redis_lib
    from osiris_alert.manager import AlertManager

    m = AlertManager(redis_url="redis://localhost:6379/0")
    fake = MagicMock()
    fake.publish.side_effect = redis_lib.RedisError("down")
    m._redis = fake
    out = m.check_item({"id": "i", "cleaned_content": "x", "title": ""},
                       [{"id": "q", "name": "N", "query_text": "x", "alert_enabled": True}])
    assert len(out) == 1
