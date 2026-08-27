"""Query Engine — tam metin ve semantik arama.

Bkz. doküman §5.4.
"""

from __future__ import annotations

from typing import Any

import psycopg


class QueryEngine:
    """PostgreSQL full-text + pgvector semantik arama."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url)

    def fulltext_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Tam metin arama (tsvector)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, url, cleaned_content, collected_at
                FROM items
                WHERE to_tsvector('simple', cleaned_content) @@ plainto_tsquery('simple', %s)
                ORDER BY ts_rank(to_tsvector('simple', cleaned_content),
                                 plainto_tsquery('simple', %s)) DESC
                LIMIT %s
                """,
                (query, query, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def semantic_search(self, embedding: list[float], limit: int = 20) -> list[dict[str, Any]]:
        """pgvector kosinüs benzerliği ile semantik arama."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, title, url, cleaned_content, collected_at,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM items
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding, embedding, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def entity_search(self, entity_type: str, value: str, limit: int = 20) -> list[dict[str, Any]]:
        """Varlık bazlı arama."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT i.id, i.title, i.url, i.cleaned_content
                FROM items i
                JOIN item_entities ie ON ie.item_id = i.id
                JOIN entities e ON e.id = ie.entity_id
                WHERE e.type = %s AND e.value ILIKE %s
                LIMIT %s
                """,
                (entity_type, f"%{value}%", limit),
            ).fetchall()
        return [dict(row) for row in rows]
