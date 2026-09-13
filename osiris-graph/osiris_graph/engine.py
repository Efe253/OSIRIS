"""Graph Engine — varlıklar arası ilişki grafı analizi.

Bkz. doküman §5.5.
"""

from __future__ import annotations

import json
from typing import Any

import networkx as nx


class GraphEngine:
    """Varlık ilişki grafını oluşturur ve analiz eder."""

    def __init__(self, max_nodes: int = 100_000) -> None:
        self.graph = nx.Graph()
        self.max_nodes = max_nodes

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
        if self.graph.number_of_nodes() >= self.max_nodes and not (
            self.graph.has_node(source) and self.graph.has_node(target)
        ):
            raise OverflowError("Graf düğüm limiti aşıldı")
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
        if not self.graph.has_node(entity_id):
            return []
        return list(self.graph.neighbors(entity_id))

    def to_json(self) -> str:
        """Grafı JSON olarak dışa aktarır (GEXF/GraphML yerine hafif format)."""
        nodes = [
            {"id": nid, **attrs}
            for nid, attrs in self.graph.nodes(data=True)
        ]
        edges = [
            {
                "source": u,
                "target": v,
                **attrs,
            }
            for u, v, attrs in self.graph.edges(data=True)
        ]
        return json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False)

    def export_graphml(self, path: str) -> None:
        """Grafı GraphML olarak dışa aktarır."""
        nx.write_graphml(self.graph, path)

    def export_gexf(self, path: str) -> None:
        """Grafı GEXF olarak dışa aktarır."""
        nx.write_gexf(self.graph, path)
