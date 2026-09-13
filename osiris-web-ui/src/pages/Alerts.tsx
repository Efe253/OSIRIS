import { useEffect, useState } from "react";
import { del, get, post, type SavedQuery } from "../api";
import { useAuth } from "../auth";

const inputCls =
  "w-full rounded-lg border border-osiris-panel bg-osiris-bg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none";

export default function Alerts() {
  const { role } = useAuth();
  const canWrite = role !== "viewer";
  const [queries, setQueries] = useState<SavedQuery[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [text, setText] = useState("");
  const [testText, setTestText] = useState("");
  const [testResult, setTestResult] = useState<{ query_name: string; matched: string }[] | null>(null);

  const refresh = async () => {
    try {
      setQueries(await get<SavedQuery[]>("/saved-queries"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yüklenemedi");
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await post("/saved-queries", { name, query_text: text, query_type: "fts", alert_enabled: true });
      setName("");
      setText("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Oluşturulamadı");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Sorgu silinsin mi?")) return;
    try {
      await del(`/saved-queries/${id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Silinemedi");
    }
  };

  const runTest = async () => {
    setError(null);
    setTestResult(null);
    try {
      setTestResult(await post("/alerts/test", { text: testText }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test başarısız");
    }
  };

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Uyarılar ({queries.length})</h2>
      {error && <p className="mb-3 text-sm text-red-400">Hata: {error}</p>}

      {canWrite && (
      <form onSubmit={create} className="mb-6 flex flex-col gap-2 rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4 sm:flex-row">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Kural adı *" required className={inputCls} />
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Anahtar kelime *" required className={inputCls} />
        <button className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent">Ekle</button>
      </form>
      )}

      <ul className="mb-8 space-y-2">
        {queries.map((q) => (
          <li key={q.id} className="flex items-center justify-between rounded-lg border border-osiris-panel bg-osiris-panel/40 px-4 py-2">
            <div>
              <span className="font-medium">{q.name}</span>
              <span className="ml-3 text-sm text-slate-400">“{q.query_text}”</span>
              {!q.alert_enabled && <span className="ml-2 text-xs text-slate-600">(kapalı)</span>}
            </div>
            {canWrite && (
            <button onClick={() => remove(q.id)} className="rounded border border-osiris-panel px-2 py-1 text-xs text-red-400 hover:bg-red-400/10">
              Sil
            </button>
            )}
          </li>
        ))}
        {queries.length === 0 && <li className="text-sm text-slate-500">Kayıtlı sorgu yok.</li>}
      </ul>

      <h3 className="mb-2 text-base font-semibold">Metin Deneme</h3>
      <p className="mb-2 text-xs text-slate-500">Bir metni kayıtlı kurallara karşı test edin (kayıt oluşmaz).</p>
      <div className="flex gap-2">
        <input value={testText} onChange={(e) => setTestText(e.target.value)} placeholder="Denenecek metin..." className={inputCls} />
        <button onClick={runTest} disabled={!testText.trim()} className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent disabled:opacity-40">
          Dene
        </button>
      </div>
      {testResult !== null && (
        <p className="mt-2 text-sm text-slate-400">
          {testResult.length === 0
            ? "Eşleşme yok."
            : `Eşleşen: ${testResult.map((t) => `${t.query_name} (“${t.matched}”)`).join(", ")}`}
        </p>
      )}
    </section>
  );
}
