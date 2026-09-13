"""Embedding aşaması testleri (model yokken graceful davranış)."""

import json

from osiris_pipeline.pipeline import ProcessingPipeline


def test_generate_embedding_without_model_returns_none() -> None:
    p = ProcessingPipeline.__new__(ProcessingPipeline)
    p.embedding_model_name = None
    p._embedder = None
    assert p.generate_embedding("merhaba dünya") is None
    assert p.generate_embedding("") is None
    assert p.embedder is None


def test_process_one_includes_embedding_key() -> None:
    p = ProcessingPipeline.__new__(ProcessingPipeline)
    p.embedding_model_name = None
    p._embedder = None
    p._nlp = False
    raw = json.dumps({"plugin_id": "rss", "item": {"raw_content": "test"}})
    result = p.process_one(raw)
    assert "embedding" in result
    assert result["embedding"] is None
