import { useState } from "react";
import { post, type SearchHit } from "../api";

const inputCls =
  "w-full rounded-lg border border-osiris-panel bg-osiris-panel/40 px-4 py-2 text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none";

type Mode = "fts" | "entity";

export default function Search() {
  const [mode, setMode] = useState<Mode>("fts");
  const [query, setQuery] = useState("");
  const [entityType, setEntityType] = useState("domain");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [searched, setSearched] = useState(false);

  const run = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res =
        mode === "fts"
          ? await post<SearchHit[]>("/search", { query, limit: 20 })
          : await post<SearchHit[]>("/search/entity", { entity_type: entityType, value: query, limit: 20 });
      setHits(res);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Arama başarısız");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Arama</h2>
      <div className="mb-3 flex gap-2">
        {(["fts", "entity"] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded px-3 py-1 text-sm ${
              mode === m ? "bg-osiris-accent/20 text-osiris-accent" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {m === "fts" ? "Tam Metin" : "Varlık"}
          </button>
        ))}
      </div>
      <form onSubmit={run} className="flex gap-2">
        {mode === "entity" && (
          <select value={entityType} onChange={(e) => setEntityType(e.target.value)} className="rounded-lg border border-osiris-panel bg-osiris-panel/40 px-3 py-2 text-sm">
            {["person", "org", "location", "ip", "domain", "email", "phone", "crypto_address", "hash", "username", "cve", "custom"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        )}
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={mode === "fts" ? "Anahtar kelime..." : "Varlık değeri..."}
          className={inputCls}
        />
        <button disabled={busy || !query.trim()} className="rounded-lg bg-osiris-accent/20 px-5 py-2 font-semibold text-osiris-accent disabled:opacity-40">
          {busy ? "..." : "Ara"}
        </button>
      </form>
      {error && <p className="mt-3 text-sm text-red-400">Hata: {error}</p>}
      {searched && !error && (
        <p className="mt-4 text-sm text-slate-500">{hits.length} sonuç</p>
      )}
      <ul className="mt-2 space-y-2">
        {hits.map((h) => (
          <li key={h.id} className="rounded-lg border border-osiris-panel bg-osiris-panel/40 p-3">
            <div className="font-medium">{h.title || "(başlıksız)"}</div>
            <div className="truncate text-xs text-osiris-accent/80">{h.url}</div>
            {h.cleaned_content && <p className="mt-1 line-clamp-3 text-sm text-slate-400">{h.cleaned_content}</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}
