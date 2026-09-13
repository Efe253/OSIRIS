import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface AuthState {
  ready: boolean;
  role: string | null;
  login: (apiKey: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  ready: false,
  role: null,
  login: async () => undefined,
  logout: () => undefined,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<string | null>(() => sessionStorage.getItem("osiris_role"));
  const [ready, setReady] = useState(() => !!sessionStorage.getItem("osiris_key"));

  const login = useCallback(async (apiKey: string) => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 15000);
    try {
      // Önce anahtarı doğrula (hafif uç)
      const me = await fetch("/api/plugins", {
        headers: { "X-API-Key": apiKey },
        signal: ctrl.signal,
      });
      if (!me.ok) throw new Error(me.status === 401 ? "Anahtar geçersiz" : `HTTP ${me.status}`);
      // Rolü uç yoklamasıyla çöz (admin → analyst → viewer).
      // Not: yalnızca 200 kabul edilir (500'ler rol şişirmez).
      const headers = { "X-API-Key": apiKey, "Content-Type": "application/json" };
      let resolved = "viewer";
      if ((await fetch("/api/auth/keys", { headers, signal: ctrl.signal })).ok) {
        resolved = "admin";
      } else if (
        (
          await fetch("/api/alerts/test", {
            method: "POST",
            headers,
            body: JSON.stringify({ text: "rol yoklaması" }),
            signal: ctrl.signal,
          })
        ).status === 200
      ) {
        resolved = "analyst";
      }
      // Doğrulama bitmeden saklama (yarım oturum kalmasın)
      sessionStorage.setItem("osiris_key", apiKey);
      sessionStorage.setItem("osiris_role", resolved);
      setRole(resolved);
      setReady(true);
    } catch (err) {
      sessionStorage.removeItem("osiris_key");
      sessionStorage.removeItem("osiris_role");
      if (err instanceof DOMException && err.name === "AbortError") {
        throw new Error("Sunucu yanıt vermiyor (15 sn)");
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem("osiris_key");
    sessionStorage.removeItem("osiris_jwt");
    sessionStorage.removeItem("osiris_role");
    setRole(null);
    setReady(false);
  }, []);

  return <AuthContext.Provider value={{ ready, role, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
