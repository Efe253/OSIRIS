"""Processing Pipeline testleri."""

import pytest

from osiris_pipeline.pipeline import ProcessingPipeline


@pytest.fixture
def pipeline() -> ProcessingPipeline:
    return ProcessingPipeline()


def test_clean_strips_html(pipeline: ProcessingPipeline) -> None:
    html = "<html><body><h1>Başlık</h1><p>İçerik   metni</p></body></html>"
    assert pipeline.clean(html) == "Başlık İçerik metni"


def test_detect_language(pipeline: ProcessingPipeline) -> None:
    assert pipeline.detect_language("Bu bir Türkçe cümledir.") == "tr"


def test_extract_entities_email_ip_domain(pipeline: ProcessingPipeline) -> None:
    text = "İletişim: test@example.com, sunucu 192.168.1.1, site example.org"
    entities = pipeline.extract_entities(text)
    types = {e["type"] for e in entities}
    assert "email" in types
    assert "ip" in types
    assert "domain" in types
