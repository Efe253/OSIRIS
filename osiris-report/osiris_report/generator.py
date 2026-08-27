"""Report Generator — analiz sonuçlarını rapora dönüştürür.

Bkz. doküman §5.7.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

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

    def __init__(self, template_dir: str | None = None) -> None:
        self.env = Environment(loader=FileSystemLoader(template_dir) if template_dir else None)

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
            title=title,
            generated_at=datetime.utcnow().isoformat(),
            scope=scope,
            summary=summary,
            findings=findings,
            sources=sources,
        )

    def generate_json(self, data: dict[str, Any]) -> str:
        """JSON rapor üretir."""
        return json.dumps(data, ensure_ascii=False, indent=2)

    def generate_csv(self, rows: list[dict[str, Any]], path: str) -> None:
        """CSV rapor üretir."""
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def save(self, content: str, path: str) -> Path:
        """Raporu diske yazar."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        return out
