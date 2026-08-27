"""Graph Engine — varlıklar arası ilişki grafı analizi.

Bkz. doküman §5.5.
"""

from __future__ import annotations

import json
from typing import Any

import networkx as nx


class GraphEngine:
    """Varlık ilişki grafını oluşturur ve analiz eder."""

    def __init__(self) -> None:
        self.graph = nx.Graph()

    def add_relation(
        self,
        source: str,
        target: str,
        relation_type: str = "related",
        weight: float = 1.0,
    ) -> None:
        """İki varlık arasına ağırlıklı bir kenar ekler."""
        self.graph.add_edge(source, target, relation_type=relation_type, weight=weight)

    def add_entity(self, entity_id: str, **attrs: Any) -> None:
        """Grafa bir düğüm ekler."""
        self.graph.add_node(entity_id, **attrs)

    def centrality(self) -> dict[str, float]:
        """Merkezi düğüm tespiti (degree centrality)."""
        return dict(nx.degree_centrality(self.graph))

    def communities(self) -> list[list[str]]:
        """Kümeleme (community detection) — greedy modularity."""
        communities = nx.community.greedy_modularity_communities(self.graph)
        return [list(c) for c in communities]

    def neighbors(self, entity_id: str) -> list[str]:
        """Bir varlığın komşularını döndürür."""
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
