import { useState } from "react";
import { useAuth } from "../auth";

export default function Login() {
  const { login } = useAuth();
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(key.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Giriş başarısız");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-lg border border-osiris-panel bg-osiris-panel/40 p-8"
      >
        <h1 className="mb-1 text-2xl font-bold tracking-widest text-osiris-accent">OSIRIS</h1>
        <p className="mb-6 text-sm text-slate-400">
          Devam etmek için API anahtarınızı girin (operatör veya kullanıcı anahtarı).
        </p>
        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder="osiris_... veya operatör anahtarı"
          autoComplete="off"
          className="w-full rounded-lg border border-osiris-panel bg-osiris-bg px-4 py-2 text-slate-200 placeholder-slate-500 focus:border-osiris-accent focus:outline-none"
        />
        {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={busy || !key.trim()}
          className="mt-4 w-full rounded-lg bg-osiris-accent/20 px-4 py-2 font-semibold text-osiris-accent transition hover:bg-osiris-accent/30 disabled:opacity-40"
        >
          {busy ? "Doğrulanıyor..." : "Giriş"}
        </button>
        <p className="mt-4 text-xs text-slate-500">
          Anahtar yalnızca bu sekmede (sessionStorage) tutulur, diske yazılmaz.
        </p>
      </form>
    </div>
  );
}
