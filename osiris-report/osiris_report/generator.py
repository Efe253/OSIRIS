"""Report Generator — analiz sonuçlarını rapora dönüştürür.

Bkz. doküman §5.7.
"""

from __future__ import annotations

import csv
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, FileSystemLoader

_TEMPLATE = """# {{ title }}

**Oluşturulma:** {{ generated_at }}
**Kapsam:** {{ scope }}

## Özet

{{ summary }}

## Bulgular

{% for finding in findings %}
### {{ finding.title }}
{{ finding.description }}

{% endfor %}
## Kaynaklar

{% for source in sources %}
- {{ source }}
{% endfor %}
"""


class ReportGenerator:
    """Raporları Markdown, JSON ve CSV olarak üretir."""

    def __init__(self, template_dir: str | None = None, output_dir: str | Path = "reports") -> None:
        if template_dir:
            tdir = Path(template_dir).resolve()
            self.env = Environment(
                loader=FileSystemLoader(str(tdir)),
                autoescape=True,
            )
        else:
            self.env = Environment(loader=BaseLoader(), autoescape=True)
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _safe_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, str]]:
        clean = []
        for f in findings[:500]:
            if not isinstance(f, dict):
                continue
            clean.append(
                {
                    "title": str(f.get("title", ""))[:500],
                    "description": str(f.get("description", ""))[:5000],
                }
            )
        return clean

    def generate_markdown(
        self,
        title: str,
        scope: str,
        summary: str,
        findings: list[dict[str, Any]],
        sources: list[str],
    ) -> str:
        """Markdown rapor üretir."""
        template = self.env.from_string(_TEMPLATE)
        return template.render(
            title=str(title)[:500],
            generated_at=datetime.now(UTC).isoformat(),
            scope=str(scope)[:1000],
            summary=str(summary)[:20000],
            findings=self._safe_findings(findings),
            sources=[str(s)[:1000] for s in sources[:500]],
        )

    def generate_json(self, data: dict[str, Any]) -> str:
        """JSON rapor üretir."""
        return json.dumps(data, ensure_ascii=False, indent=2)

    # STIX 2.1 varlık eşleşmesi (doküman §2.6 — tehdit istihbaratı formatı)
    _STIX_IOC = {
        "ip": ("ipv4-addr", "value"),
        "domain": ("domain-name", "value"),
        "email": ("email-addr", "value"),
        "crypto_address": ("cryptocurrency-wallet", "value"),
        "hash": ("file", "hashes.MD5"),
        "cve": ("vulnerability", "name"),
    }

    def generate_stix(self, identity_name: str, title: str,
                      entities: list[dict[str, Any]]) -> str:
        """STIX 2.1 Bundle üretir (identity + indicator + observed-data)."""
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        bundle_id = f"bundle--{uuid.uuid4()}"
        identity_id = f"identity--{uuid.uuid5(uuid.NAMESPACE_DNS, 'osiris.local')}"
        objects: list[dict[str, Any]] = [
            {
                "type": "identity",
                "spec_version": "2.1",
                "id": identity_id,
                "created": now,
                "modified": now,
                "name": str(identity_name)[:200] or "OSIRIS",
                "identity_class": "system",
            }
        ]
        for ent in entities[:500]:
            if not isinstance(ent, dict):
                continue
            etype = str(ent.get("type", "custom"))
            value = str(ent.get("value", ""))[:500]
            if not value or etype not in self._STIX_IOC:
                continue
            stix_type, prop = self._STIX_IOC[etype]
            obj_id = f"{stix_type}--{uuid.uuid5(uuid.NAMESPACE_URL, f'{etype}:{value.lower()}')}"
            if etype == "cve":
                objects.append({
                    "type": "vulnerability",
                    "spec_version": "2.1",
                    "id": obj_id,
                    "created": now,
                    "modified": now,
                    "name": value.upper(),
                    "created_by_ref": identity_id,
                })
            elif etype == "hash":
                objects.append({
                    "type": "file",
                    "spec_version": "2.1",
                    "id": obj_id,
                    "hashes": {"MD5": value},
                    "created_by_ref": identity_id,
                })
            else:
                pattern = f"[{stix_type}:{prop} = '{value}']"
                objects.append({
                    "type": "indicator",
                    "spec_version": "2.1",
                    "id": f"indicator--{uuid.uuid5(uuid.NAMESPACE_URL, pattern)}",
                    "created": now,
                    "modified": now,
                    "pattern": pattern,
                    "pattern_type": "stix",
                    "valid_from": now,
                    "labels": ["malicious-activity"],
                    "created_by_ref": identity_id,
                    "object_marking_refs": [],
                    "description": f"OSIRIS: {title}"[:500],
                })
        bundle = {
            "type": "bundle",
            "id": bundle_id,
            "spec_version": "2.1",
            "objects": objects,
        }
        return json.dumps(bundle, ensure_ascii=False, indent=2)

    @staticmethod
    def _csv_safe(value: Any) -> Any:
        # CSV formül enjeksiyonu koruması (=, +, -, @, tab/CR ile başlayan hücreler)
        if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + value
        return value

    def generate_csv(self, rows: list[dict[str, Any]], path: str) -> None:
        """CSV rapor üretir (output_dir dışına yazmaz)."""
        if not rows:
            return
        out = self._resolve_output_path(path, suffix=".csv")
        fieldnames = list(rows[0].keys())[:50]
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows[:10000]:
                writer.writerow({k: self._csv_safe(row.get(k)) for k in fieldnames})

    def _resolve_output_path(self, path: str, suffix: str = "") -> Path:
        out = (self.output_dir / Path(path).name).resolve()
        if self.output_dir not in out.parents and out != self.output_dir:
            raise ValueError("Çıktı dizini dışına yazma engellendi")
        if suffix and out.suffix != suffix:
            out = out.with_suffix(suffix)
        out.parent.mkdir(parents=True, exist_ok=True)
        return out

    def save(self, content: str, path: str) -> Path:
        """Raporu diske yazar (yalnızca output_dir altına)."""
        if len(content) > 5_000_000:
            raise ValueError("Rapor çok büyük")
        out = self._resolve_output_path(path)
        out.write_text(content, encoding="utf-8")
        return out
