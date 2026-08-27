import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Sources from "./pages/Sources";
import Search from "./pages/Search";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/sources", label: "Kaynaklar" },
  { to: "/search", label: "Arama" },
];

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-osiris-panel bg-osiris-panel/60 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold tracking-widest text-osiris-accent">
            OSIRIS
          </h1>
          <nav className="flex gap-4">
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
        </div>
      </header>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/search" element={<Search />} />
        </Routes>
      </main>
    </div>
  );
}
