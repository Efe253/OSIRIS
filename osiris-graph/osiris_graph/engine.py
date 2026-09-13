"""Graph Engine — varlıklar arası ilişki grafı analizi.

Bkz. doküman §5.5.
"""

from __future__ import annotations

import json
import math
import threading
from typing import Any

import networkx as nx


class GraphEngine:
    """Varlık ilişki grafını oluşturur ve analiz eder."""

    def __init__(self, max_nodes: int = 100_000,
                 database_url: str | None = None) -> None:
        self.graph = nx.Graph()
        self.max_nodes = max_nodes
        self.database_url = database_url
        self._lock = threading.RLock()

    def _validate_id(self, entity_id: str) -> str:
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise ValueError("entity_id boş olamaz")
        eid = entity_id.strip()
        if len(eid) > 500:
            raise ValueError("entity_id çok uzun")
        return eid

    def add_relation(
        self,
        source: str,
        target: str,
        relation_type: str = "related",
        weight: float = 1.0,
    ) -> None:
        """İki varlık arasına ağırlıklı bir kenar ekler."""
        source, target = self._validate_id(source), self._validate_id(target)
        if source == target:
            return
        try:
            weight = float(weight)
        except (TypeError, ValueError) as exc:
            raise ValueError("weight sayı olmalı") from exc
        if not math.isfinite(weight):
            raise ValueError("weight sonlu sayı olmalı")
        if self.graph.number_of_nodes() >= self.max_nodes and not (
            self.graph.has_node(source) and self.graph.has_node(target)
        ):
            raise OverflowError("Graf düğüm limiti aşıldı")
        with self._lock:
            self.graph.add_edge(
                source, target,
                relation_type=str(relation_type)[:100], weight=weight,
            )

    def add_entity(self, entity_id: str, **attrs: Any) -> None:
        """Grafa bir düğüm ekler."""
        eid = self._validate_id(entity_id)
        if self.graph.number_of_nodes() >= self.max_nodes and not self.graph.has_node(eid):
            raise OverflowError("Graf düğüm limiti aşıldı")
        safe_attrs = {str(k)[:100]: str(v)[:1000] for k, v in list(attrs.items())[:20]}
        with self._lock:
            self.graph.add_node(eid, **safe_attrs)

    def centrality(self) -> dict[str, float]:
        """Merkezi düğüm tespiti (degree centrality)."""
        if self.graph.number_of_nodes() == 0:
            return {}
        return dict(nx.degree_centrality(self.graph))

    def communities(self) -> list[list[str]]:
        """Kümeleme (community detection) — greedy modularity."""
        if self.graph.number_of_nodes() == 0:
            return []
        if self.graph.number_of_edges() == 0:
            return [[n] for n in self.graph.nodes]
        communities = nx.community.greedy_modularity_communities(self.graph)
        return [list(c) for c in communities]

    def neighbors(self, entity_id: str) -> list[str]:
        """Bir varlığın komşularını döndürür (yoksa boş liste)."""
        with self._lock:
            if not self.graph.has_node(entity_id):
                return []
            return list(self.graph.neighbors(entity_id))

    def to_json(self, limit_nodes: int = 5000, limit_edges: int = 20000) -> str:
        """Grafı JSON olarak dışa aktarır (DoS korumalı üst sınırlarla)."""
        with self._lock:
            nodes = [
                {"id": nid, **attrs}
                for nid, attrs in list(self.graph.nodes(data=True))[:max(0, limit_nodes)]
            ]
            edges = [
                {
                    "source": u,
                    "target": v,
                    **attrs,
                }
                for u, v, attrs in list(self.graph.edges(data=True))[:max(0, limit_edges)]
            ]
        return json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)

    @staticmethod
    def _check_export_path(path: str) -> None:
        if not path or not isinstance(path, str) or len(path) > 1024:
            raise ValueError("Dışa aktarım yolu geçersiz")

    def export_graphml(self, path: str) -> None:
        """Grafı GraphML olarak dışa aktarır."""
        self._check_export_path(path)
        nx.write_graphml(self.graph, path)

    def export_gexf(self, path: str) -> None:
        """Grafı GEXF olarak dışa aktarır."""
        self._check_export_path(path)
        nx.write_gexf(self.graph, path)

    def save_to_db(self) -> int:
        """Bellekteki kenarları `graph_edges` tablosuna yazar (upsert).

        Dönen: yazılan kenar sayısı. database_url yoksa 0 döner.
        """
        if not self.database_url:
            return 0
        import psycopg

        with self._lock:
            edges = [
                (str(u)[:500], str(v)[:500], str(d.get("relation_type", "related"))[:100],
                 float(d.get("weight", 1.0)))
                for u, v, d in list(self.graph.edges(data=True))
            ]
        if not edges:
            return 0
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO graph_edges
                        (source_name, target_name, relation_type, weight, last_seen_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (source_name, target_name, relation_type)
                    DO UPDATE SET weight = EXCLUDED.weight,
                                  evidence_count = graph_edges.evidence_count + 1,
                                  last_seen_at = NOW()
                    """,
                    edges,
                )
            conn.commit()
        return len(edges)

    def load_from_db(self, limit: int = 10000) -> int:
        """`graph_edges` tablosundaki kenarları belleğe yükler.

        Dönen: yüklenen kenar sayısı. database_url yoksa 0 döner.
        """
        try:
            limit = max(1, min(int(limit), 100_000))
        except (TypeError, ValueError) as exc:
            raise ValueError("limit geçersiz") from exc
        if not self.database_url:
            return 0
        import psycopg

        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_name, target_name, relation_type, weight
                    FROM graph_edges
                    ORDER BY last_seen_at DESC LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        loaded = 0
        for source, target, relation_type, weight in rows:
            try:
                self.add_relation(source, target, relation_type, weight)
                loaded += 1
            except (ValueError, OverflowError):
                continue
        return loaded
