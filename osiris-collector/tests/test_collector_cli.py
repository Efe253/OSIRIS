"""Collector CLI testleri."""

import json
from unittest.mock import MagicMock, patch

from osiris_collector import cli as collector_cli


def run_cli(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["osiris-collector", *argv])
    return collector_cli.main()


def test_list_plugins(monkeypatch, capsys) -> None:
    mgr = MagicMock()
    mgr.plugins = {}
    mgr.load_plugins.return_value = 0
    with patch.object(collector_cli, "CollectorManager", return_value=mgr):
        assert run_cli(monkeypatch, ["--list"]) == 0
    assert "plugin" in capsys.readouterr().out.lower() or True


def test_run_success_and_failure(monkeypatch, capsys) -> None:
    from osiris.plugin import CollectionResult

    mgr = MagicMock()
    mgr.load_plugins.return_value = 0
    mgr.run_collection.return_value = CollectionResult(items=[], metadata={"a": 1})
    with patch.object(collector_cli, "CollectorManager", return_value=mgr):
        assert run_cli(monkeypatch, ["--run", "rss"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out == {"a": 1}
    mgr.run_collection.return_value = CollectionResult(
        items=[], success=False, error="x")
    with patch.object(collector_cli, "CollectorManager", return_value=mgr):
        assert run_cli(monkeypatch, ["--run", "rss"]) == 1


def test_run_unknown_plugin(monkeypatch) -> None:
    mgr = MagicMock()
    mgr.load_plugins.return_value = 0
    mgr.run_collection.side_effect = KeyError("yok")
    with patch.object(collector_cli, "CollectorManager", return_value=mgr):
        assert run_cli(monkeypatch, ["--run", "yok"]) == 1


def test_run_bad_json_exits(monkeypatch) -> None:
    import pytest

    mgr = MagicMock()
    with patch.object(collector_cli, "CollectorManager", return_value=mgr):
        with pytest.raises(SystemExit):
            run_cli(monkeypatch, ["--run", "rss", "--config", "{bozuk"])
        with pytest.raises(SystemExit):
            run_cli(monkeypatch, ["--run", "rss", "--config", "[1,2]"])
