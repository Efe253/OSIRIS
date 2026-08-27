export default function Search() {
  return (
    <section>
      <h2 className="mb-4 text-lg font-semibold">Arama</h2>
      <input
        type="text"
        placeholder="Tam metin, varlık veya semantik arama..."
        className="w-full rounded-lg border border-osiris-panel bg-osiris-panel/40 px-4 py-2 text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none"
      />
      <p className="mt-4 text-sm text-slate-500">
        Faz 3 — Query Engine entegrasyonuyla tam metin ve semantik arama.
      </p>
    </section>
  );
}
