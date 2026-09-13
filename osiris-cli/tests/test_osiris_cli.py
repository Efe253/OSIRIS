"""osiris CLI testleri (click CliRunner)."""

from click.testing import CliRunner
from osiris_cli.cli import main


def test_status_and_version() -> None:
    runner = CliRunner()
    assert runner.invoke(main, ["status"]).exit_code == 0
    assert "OSIRIS" in runner.invoke(main, ["status"]).output
    assert runner.invoke(main, ["--version"]).exit_code == 0


def test_plugins_lists_all() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["plugins"])
    assert result.exit_code == 0
    assert "plugin yüklendi" in result.output
    assert "irc" in result.output  # stdlib-only, her ortamda yüklenir


def test_collect_bad_json_and_shape() -> None:
    runner = CliRunner()
    assert runner.invoke(main, ["collect", "rss", "--config", "{bozuk"]).exit_code == 2
    assert runner.invoke(main, ["collect", "rss", "--config", "[1]"]).exit_code == 2


def test_collect_unknown_plugin() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["collect", "yok-boyle-plugin"])
    assert result.exit_code == 1
    assert "bulunamadı" in result.output


def test_collect_failure_path() -> None:
    # rss {} ile deterministic başarısız olur (feed_url yok) → çıkış 1
    runner = CliRunner()
    result = runner.invoke(main, ["collect", "rss", "--config", "{}"])
    assert result.exit_code == 1
    assert "Hata" in result.output or "bulunamadı" in result.output
