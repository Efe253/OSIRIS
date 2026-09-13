import { useState } from "react";
import { post } from "../api";

const inputCls =
  "w-full rounded-lg border border-osiris-panel bg-osiris-bg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none";
const areaCls = `${inputCls} min-h-24 font-mono text-xs`;

export default function Reports() {
  const [title, setTitle] = useState("");
  const [scope, setScope] = useState("");
  const [summary, setSummary] = useState("");
  const [findingsText, setFindingsText] = useState("");
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const findings = findingsText
        .split("\n")
        .map((l) => l.trim())
        .filter(Boolean)
        .map((l) => {
          const [t, ...rest] = l.split("|");
          return { title: t.trim(), description: rest.join("|").trim() };
        });
      const res = await post<{ markdown: string }>("/reports/markdown", {
        title,
        scope,
        summary,
        findings,
        sources: [],
      });
      setMarkdown(res.markdown);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Üretilemedi");
    } finally {
      setBusy(false);
    }
  };

  const download = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${title || "rapor"}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Rapor Üretici</h2>
      {error && <p className="mb-3 text-sm text-red-400">Hata: {error}</p>}
      <form onSubmit={generate} className="space-y-3 rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Başlık *" required className={inputCls} />
        <input value={scope} onChange={(e) => setScope(e.target.value)} placeholder="Kapsam" className={inputCls} />
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Özet" className={areaCls} />
        <textarea value={findingsText} onChange={(e) => setFindingsText(e.target.value)} placeholder="Bulgu başlığı | Açıklama (satır başına bir bulgu)" className={areaCls} />
        <button disabled={busy} className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent disabled:opacity-40">
          {busy ? "Üretiliyor..." : "Rapor Üret"}
        </button>
      </form>
      {markdown && (
        <div className="mt-4">
          <div className="mb-2 flex justify-end">
            <button onClick={download} className="rounded border border-osiris-panel px-3 py-1 text-sm text-osiris-accent hover:bg-osiris-accent/10">
              .md indir
            </button>
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border border-osiris-panel bg-osiris-bg p-4 font-mono text-xs text-slate-300">
            {markdown}
          </pre>
        </div>
      )}
    </section>
  );
}
