"""STIX 2.1 rapor testleri."""

import json

from osiris_report.generator import ReportGenerator


def test_generate_stix_bundle_structure() -> None:
    rg = ReportGenerator(output_dir="/tmp/opencode/reports-stix")
    raw = rg.generate_stix(
        "OSIRIS-Test",
        "Test Raporu",
        [
            {"type": "ip", "value": "1.2.3.4"},
            {"type": "domain", "value": "evil.example"},
            {"type": "cve", "value": "cve-2024-1234"},
            {"type": "person", "value": "Ali"},  # IOC değil → atlanır
            {"type": "email", "value": "a@b.co"},
        ],
    )
    bundle = json.loads(raw)
    assert bundle["type"] == "bundle"
    assert bundle["spec_version"] == "2.1"
    types = [o["type"] for o in bundle["objects"]]
    assert "identity" in types
    assert "indicator" in types
    assert "vulnerability" in types
    assert not any(o.get("name") == "Ali" for o in bundle["objects"])
    vuln = next(o for o in bundle["objects"] if o["type"] == "vulnerability")
    assert vuln["name"] == "CVE-2024-1234"


def test_generate_stix_empty_entities() -> None:
    rg = ReportGenerator(output_dir="/tmp/opencode/reports-stix")
    bundle = json.loads(rg.generate_stix("X", "T", []))
    assert len(bundle["objects"]) == 1  # yalnızca identity


def test_generate_html_escapes() -> None:
    rg = ReportGenerator(output_dir="/tmp/opencode/reports-html")
    html = rg.generate_html("T", "S", "O", [{"title": "<b>B</b>", "description": "D"}], ["s"])
    assert "<b>B</b>" not in html
    assert "&lt;b&gt;" in html
    assert html.startswith("<!DOCTYPE html>")


def test_ipv6_maps_to_ipv6_addr() -> None:
    import json

    from osiris_report.generator import ReportGenerator

    rg = ReportGenerator(output_dir="/tmp/opencode/reports-ipv6")
    bundle = json.loads(rg.generate_stix(
        "X", "T", [{"type": "ip", "value": "::1"}]))
    kinds = {o["type"] for o in bundle["objects"]}
    patterns = [o.get("pattern", "") for o in bundle["objects"]]
    assert any("ipv6-addr" in p for p in patterns)
    assert "identity" in kinds
