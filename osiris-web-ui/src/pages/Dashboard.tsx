export default function Dashboard() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Genel Bakış</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { label: "Toplam Kaynak", value: "—" },
          { label: "Toplanan Öğe", value: "—" },
          { label: "Aktif Uyarı", value: "—" },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-lg border border-osiris-panel bg-osiris-panel/40 p-4"
          >
            <div className="text-sm text-slate-400">{card.label}</div>
            <div className="mt-1 text-2xl font-bold text-osiris-accent">
              {card.value}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-6 text-sm text-slate-500">
        Faz 2 — Web UI temel ekranları. Veriler API bağlantısıyla doldurulacak.
      </p>
    </section>
  );
}
