"""DB birleştirici testleri (ağ gerektirmez)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from build_full_db import as_list, convert_maigret, convert_wmn


def test_as_list_variants() -> None:
    assert as_list(None) == []
    assert as_list(["a", 1]) == ["a", "1"]
    assert as_list("tek") == ["tek"]
    assert as_list("['a', 'b']") == ["a", "b"]
    assert as_list("[bozuk") == ["[bozuk"]


def test_convert_maigret_filters() -> None:
    out, stats = convert_maigret({"sites": {
        "Ok": {"url": "https://x/{username}", "checkType": "status_code", "tags": ["dev"]},
        "Yazim": {"url": "https://x/{username}", "checkType": "message",
                  "presenseStrs": "['hos']"},
        "Motor": {"engine": "Google"},
        "Kapali": {"url": "https://x/{username}", "disabled": True},
        "Bilinmeyen": {"url": "https://x/{username}", "checkType": "captcha"},
    }})
    assert set(out) == {"Ok", "Yazim"}
    assert out["Yazim"]["presenceStrs"] == ["hos"]
    assert stats["atlanan"] == 3


def test_convert_wmn_mapping() -> None:
    out, _ = convert_wmn({"sites": [
        {"name": "A", "uri_check": "https://a/{account}",
         "e_string": "profil", "m_string": "yok", "cat": "social"},
        {"name": "B", "uri_check": "https://b/{account}"},
        {"name": "C", "uri_check": "https://sabit-yol"},
    ]})
    assert out["A"]["checkType"] == "message"
    assert out["A"]["url"] == "https://a/{username}"
    assert out["B"]["checkType"] == "status_code"
    assert "C" not in out


def test_norm_tags_canonical() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
    from build_full_db import norm_tags

    assert "dev" in norm_tags(["coding", "tech"])
    assert "social" in norm_tags("dating")
    assert norm_tags(["bilinmeyen-kategori"]) == ["bilinmeyen-kategori"]
