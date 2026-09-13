import { useEffect, useState } from "react";
import { del, get, post, type Plugin, type Source } from "../api";

const inputCls =
  "w-full rounded-lg border border-osiris-panel bg-osiris-bg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none";

function healthBadge(s: Source) {
  if (!s.last_crawled_at) return <span className="text-slate-500">hiç çalışmadı</span>;
  if (s.failure_count > 0)
    return <span className="text-red-400">hata ×{s.failure_count}</span>;
  return <span className="text-green-400">sağlıklı</span>;
}

export default function Sources() {
  const [sources, setSources] = useState<Source[]>([]);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  // form state
  const [name, setName] = useState("");
  const [pluginId, setPluginId] = useState("");
  const [url, setUrl] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});

  const refresh = async () => {
    try {
      const [s, p] = await Promise.all([get<Source[]>("/sources"), get<Plugin[]>("/plugins")]);
      setSources(s);
      setPlugins(p);
      if (!pluginId && p.length > 0) setPluginId(p[0].id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yüklenemedi");
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const schema = plugins.find((p) => p.id === pluginId)?.config_schema ?? {};
  const urlLikeKeys = ["url", "feed_url", "endpoint", "domain"];

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("create");
    setError(null);
    try {
      // Üstteki URL kutusu, şemadaki url/feed_url/endpoint/domain alanlarını besler
      const merged: Record<string, string> = { ...fields };
      if (url.trim()) {
        for (const k of urlLikeKeys) {
          if (k in schema && !merged[k]?.trim()) merged[k] = url.trim();
        }
      }
      await post("/sources", { name, plugin_id: pluginId, url, config: merged });
      setShowAdd(false);
      setName("");
      setUrl("");
      setFields({});
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Oluşturulamadı");
    } finally {
      setBusy(null);
    }
  };

  const runCollect = async (id: string) => {
    setBusy(id);
    setError(null);
    try {
      await post(`/sources/${id}/collect`, {});
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Toplama başarısız");
    } finally {
      setBusy(null);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Kaynak silinsin mi?")) return;
    setError(null);
    try {
      await del(`/sources/${id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Silinemedi");
    }
  };

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Kaynaklar ({sources.length})</h2>
        <button
          onClick={() => setShowAdd((v) => !v)}
          className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent hover:bg-osiris-accent/30"
        >
          + Kaynak Ekle
        </button>
      </div>
      {error && <p className="mb-3 text-sm text-red-400">Hata: {error}</p>}

      {showAdd && (
        <form onSubmit={create} className="mb-6 space-y-3 rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ad *" required className={inputCls} />
            <select value={pluginId} onChange={(e) => { setPluginId(e.target.value); setFields({}); }} className={inputCls}>
              {plugins.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.network_type})</option>
              ))}
            </select>
          </div>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="URL (web/rss/api/domain — plugin'e göre)" className={inputCls} />
          {Object.entries(schema).map(([key, spec]) => (
            <div key={key}>
              <label className="mb-1 block text-xs text-slate-400">
                {key} {spec.required ? "*" : ""} <span className="text-slate-600">{spec.description ?? ""}</span>
              </label>
              <input
                value={fields[key] ?? ""}
                onChange={(e) => setFields((f) => ({ ...f, [key]: e.target.value }))}
                placeholder={spec.default !== undefined ? `varsayılan: ${String(spec.default)}` : ""}
                required={!!spec.required && !(url.trim() && urlLikeKeys.includes(key))}
                className={inputCls}
              />
            </div>
          ))}
          <button disabled={busy === "create"} className="rounded-lg bg-osiris-accent/20 px-4 py-2 text-sm font-semibold text-osiris-accent disabled:opacity-40">
            {busy === "create" ? "Kaydediliyor..." : "Kaydet"}
          </button>
        </form>
      )}

      <div className="overflow-x-auto rounded-lg border border-osiris-panel">
        <table className="w-full text-left text-sm">
          <thead className="bg-osiris-panel/60 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Ad</th>
              <th className="px-4 py-2">Plugin</th>
              <th className="px-4 py-2">Durum</th>
              <th className="px-4 py-2">Son Başarı</th>
              <th className="px-4 py-2">İşlem</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id} className="border-t border-osiris-panel/50">
                <td className="px-4 py-2">
                  <div className="font-medium">{s.name}</div>
                  <div className="truncate text-xs text-slate-500">{s.url}</div>
                </td>
                <td className="px-4 py-2 text-slate-400">{s.plugin_id}</td>
                <td className="px-4 py-2">{healthBadge(s)}</td>
                <td className="px-4 py-2 text-xs text-slate-500">
                  {s.last_success_at ? new Date(s.last_success_at).toLocaleString("tr-TR") : "—"}
                  {s.avg_response_ms != null && ` · ${s.avg_response_ms}ms`}
                </td>
                <td className="px-4 py-2">
                  <div className="flex gap-2">
                    <button
                      onClick={() => runCollect(s.id)}
                      disabled={busy === s.id}
                      className="rounded border border-osiris-panel px-2 py-1 text-xs text-osiris-accent hover:bg-osiris-accent/10 disabled:opacity-40"
                    >
                      {busy === s.id ? "..." : "Çalıştır"}
                    </button>
                    <button
                      onClick={() => remove(s.id)}
                      className="rounded border border-osiris-panel px-2 py-1 text-xs text-red-400 hover:bg-red-400/10"
                    >
                      Sil
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {sources.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-slate-500">Kayıtlı kaynak yok.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
