import { useEffect, useState } from "react";
import { get, type Stats, type SearchHit } from "../api";

function Card({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-bold text-osiris-accent">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<SearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, r] = await Promise.all([
          get<Stats>("/stats"),
          get<SearchHit[]>("/items/recent?limit=5"),
        ]);
        setStats(s);
        setRecent(r);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Yüklenemedi");
      }
    })();
  }, []);

  if (error) return <p className="text-sm text-red-400">Hata: {error}</p>;
  if (!stats) return <p className="text-sm text-slate-500">Yükleniyor...</p>;

  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Genel Bakış</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Card label="Kaynak" value={`${stats.sources_enabled}/${stats.sources}`} />
        <Card label="Öğe" value={stats.items} />
        <Card label="Varlık" value={stats.entities} />
        <Card label="Graf Kenarı" value={stats.edges} />
        <Card label="Kayıtlı Sorgu" value={stats.saved_queries} />
        <Card label="Aktif Uyarı" value={stats.alerts} />
      </div>

      <h3 className="mb-3 mt-8 text-base font-semibold">Son Toplananlar</h3>
      {recent.length === 0 ? (
        <p className="text-sm text-slate-500">Henüz öğe yok — Kaynaklar sayfasından toplama başlatın.</p>
      ) : (
        <ul className="space-y-2">
          {recent.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-osiris-panel bg-osiris-panel/40 p-3"
            >
              <div className="font-medium">{item.title || "(başlıksız)"}</div>
              <div className="mt-1 truncate text-xs text-slate-500">{item.url}</div>
              {item.snippet && (
                <p className="mt-1 line-clamp-2 text-sm text-slate-400">{item.snippet}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
