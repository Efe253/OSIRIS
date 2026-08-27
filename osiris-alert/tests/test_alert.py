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
