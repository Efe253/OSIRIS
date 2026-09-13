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
    // Önce anahtarı doğrula (hafif uç), sonra JWT al
    const me = await fetch("/api/plugins", { headers: { "X-API-Key": apiKey } });
    if (!me.ok) throw new Error(me.status === 401 ? "Anahtar geçersiz" : `HTTP ${me.status}`);
    sessionStorage.setItem("osiris_key", apiKey);
    // Not: çağrılar API anahtarıyla yapılır (rol sunucuda çözülür);
    // JWT akışı harici istemciler içindir.
    // Rolü uç yoklamasıyla çöz (admin → analyst → viewer)
    const headers = { "X-API-Key": apiKey, "Content-Type": "application/json" };
    let resolved = "viewer";
    if ((await fetch("/api/auth/keys", { headers })).ok) {
      resolved = "admin";
    } else if (
      (
        await fetch("/api/alerts/test", {
          method: "POST",
          headers,
          body: JSON.stringify({ text: "rol yoklaması" }),
        })
      ).status !== 403
    ) {
      resolved = "analyst";
    }
    sessionStorage.setItem("osiris_role", resolved);
    setRole(resolved);
    setReady(true);
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
