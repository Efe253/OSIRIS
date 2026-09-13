import { HashRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Sources from "./pages/Sources";
import Search from "./pages/Search";
import Graph from "./pages/Graph";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import Login from "./pages/Login";
import { AuthProvider, useAuth } from "./auth";

const nav = [
  { to: "/", label: "Panel" },
  { to: "/sources", label: "Kaynaklar" },
  { to: "/search", label: "Arama" },
  { to: "/graph", label: "Graf" },
  { to: "/alerts", label: "Uyarılar" },
  { to: "/reports", label: "Raporlar" },
];

function Shell() {
  const { ready, role, logout } = useAuth();
  if (!ready) return <Login />;
  return (
    <div className="min-h-screen">
      <header className="border-b border-osiris-panel bg-osiris-panel/60 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-xl font-bold tracking-widest text-osiris-accent">
            OSIRIS
          </h1>
          <nav className="flex flex-wrap gap-2">
            {nav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `px-3 py-1 rounded transition ${
                    isActive
                      ? "bg-osiris-accent/20 text-osiris-accent"
                      : "text-slate-400 hover:text-slate-200"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="rounded bg-osiris-panel px-2 py-1 text-xs text-slate-400">
              rol: {role ?? "?"}
            </span>
            <button
              onClick={logout}
              className="rounded border border-osiris-panel px-3 py-1 text-sm text-slate-400 hover:text-slate-200"
            >
              Çıkış
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/search" element={<Search />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <Shell />
      </HashRouter>
    </AuthProvider>
  );
}
