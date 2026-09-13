"""ReportGenerator testleri — markdown/CSV/kayıt yolları."""

import csv
import json

import pytest
from osiris_report.generator import ReportGenerator


def rg(tmp_path):
    return ReportGenerator(output_dir=str(tmp_path))


def test_markdown_content(tmp_path) -> None:
    out = rg(tmp_path).generate_markdown(
        "Başlık", "kapsam", "özet",
        [{"title": "B1", "description": "D1"}, "bozuk"],
        ["k1"],
    )
    assert "# Başlık" in out and "B1" in out and "k1" in out


def test_json_roundtrip(tmp_path) -> None:
    data = {"a": 1}
    assert json.loads(rg(tmp_path).generate_json(data)) == data


def test_csv_and_injection_guard(tmp_path) -> None:
    r = rg(tmp_path)
    r.generate_csv([{"a": "=cmd|x", "b": "ok"}], "r.csv")
    with open(tmp_path / "r.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["a"] == "'=cmd|x"
    r.generate_csv([], "bos.csv")
    assert not (tmp_path / "bos.csv").exists()


def test_save_and_traversal_guard(tmp_path) -> None:
    r = rg(tmp_path)
    out = r.save("içerik", "rapor.md")
    assert out.read_text(encoding="utf-8") == "içerik"
    # .. içeren yol output_dir içine indirgenir (dışarı yazılmaz)
    out2 = r.save("x", "../../etc/kacis.md")
    assert out2.parent == tmp_path.resolve()
    with pytest.raises(ValueError):
        r.save("x" * 6_000_000, "buyuk.md")


def test_csv_suffix_enforced(tmp_path) -> None:
    r = rg(tmp_path)
    r.generate_csv([{"a": "1"}], "veri.txt")
    assert (tmp_path / "veri.csv").exists()
