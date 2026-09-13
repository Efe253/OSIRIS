import { useEffect, useState } from "react";
import { get, post } from "../api";

const inputCls =
  "w-full rounded-lg border border-osiris-panel bg-osiris-bg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none";

interface GraphData {
  nodes: { id: string }[];
  edges: { source: string; target: string; relation_type?: string }[];
}

export default function Graph() {
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [error, setError] = useState<string | null>(null);
  const [explore, setExplore] = useState("");
  const [neighbors, setNeighbors] = useState<string[] | null>(null);
  const [src, setSrc] = useState("");
  const [dst, setDst] = useState("");
  const [rel, setRel] = useState("related");

  const refresh = async () => {
    try {
      setGraph(await get<GraphData>("/graph"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yüklenemedi");
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const adjacency = (id: string) =>
    graph.edges.filter((e) => e.source === id || e.target === id);

  const addRelation = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await post("/graph/relation", { source: src.trim(), target: dst.trim(), relation_type: rel.trim() || "related" });
      setSrc("");
      setDst("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eklenemedi");
    }
  };

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">
        İlişki Grafı ({graph.nodes.length} düğüm, {graph.edges.length} kenar)
      </h2>
      {error && <p className="mb-3 text-sm text-red-400">Hata: {error}</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-300">Komşu Keşfi</h3>
          <div className="flex gap-2">
            <input value={explore} onChange={(e) => setExplore(e.target.value)} placeholder="Varlık id..." className={inputCls} />
            <button
              onClick={() => {
                const id = explore.trim();
                setNeighbors(id ? graph.edges.flatMap((e) => (e.source === id ? [e.target] : e.target === id ? [e.source] : [])) : null);
              }}
              className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent"
            >
              Bak
            </button>
          </div>
          {neighbors !== null && (
            <ul className="mt-3 space-y-1 text-sm">
              {neighbors.length === 0 && <li className="text-slate-500">Komşu yok.</li>}
              {neighbors.map((n) => (
                <li key={n}>
                  <button onClick={() => setExplore(n)} className="text-osiris-accent hover:underline">{n}</button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form onSubmit={addRelation} className="rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-300">İlişki Ekle</h3>
          <div className="space-y-2">
            <input value={src} onChange={(e) => setSrc(e.target.value)} placeholder="Kaynak *" required className={inputCls} />
            <input value={dst} onChange={(e) => setDst(e.target.value)} placeholder="Hedef *" required className={inputCls} />
            <input value={rel} onChange={(e) => setRel(e.target.value)} placeholder="İlişki türü" className={inputCls} />
            <button className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent">Ekle</button>
          </div>
        </form>
      </div>

      <h3 className="mb-2 mt-6 text-sm font-semibold text-slate-300">Kenarlar (son 100)</h3>
      <ul className="space-y-1 text-sm">
        {graph.edges.slice(-100).map((e, i) => (
          <li key={i} className="rounded border border-osiris-panel/50 px-3 py-1.5">
            <span className="text-slate-200">{e.source}</span>
            <span className="mx-2 text-xs text-slate-500">—[{e.relation_type ?? "related"}]→</span>
            <span className="text-slate-200">{e.target}</span>
            {adjacency(e.source).length > 3 && <span className="ml-2 text-xs text-slate-600">hub</span>}
          </li>
        ))}
        {graph.edges.length === 0 && <li className="text-slate-500">Kenar yok.</li>}
      </ul>
    </section>
  );
}
