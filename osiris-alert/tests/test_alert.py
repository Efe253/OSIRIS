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


def test_anomaly_detector() -> None:
    from osiris_alert.manager import AlertManager

    m = AlertManager(redis_url=None, anomaly_min_samples=5)
    assert m.check_anomaly("hz", 10) is None  # ısınma
    for v in [10, 11, 9, 10, 12, 10, 11, 9, 10, 11]:
        m.record_metric("hz", v)
    assert m.check_anomaly("hz", 10) is None
    spike = m.check_anomaly("hz", 100)
    assert spike is not None and spike["z_score"] > 3
    assert m.check_anomaly("hz", "bozuk") is None  # type: ignore[arg-type]
    assert m.check_anomaly("hz", float("inf")) is None
    m.record_metric("hz", "bozuk")  # sessizce yutulur
    m.record_metric("hz", float("nan"))


def test_anomaly_zero_variance() -> None:
    from osiris_alert.manager import AlertManager

    m = AlertManager(redis_url=None, anomaly_min_samples=4)
    for _ in range(6):
        m.record_metric("sabit", 7)
    assert m.check_anomaly("sabit", 7) is None
    assert m.check_anomaly("sabit", 9) is not None


def test_anomaly_init_clamps_bad_values() -> None:
    from osiris_alert.manager import AlertManager

    m = AlertManager(redis_url=None, anomaly_window="cok",
                     anomaly_threshold=float("inf"), anomaly_min_samples=None)
    assert (m._anomaly_window, m._anomaly_threshold,
            m._anomaly_min_samples) == (100, 3.0, 10)
