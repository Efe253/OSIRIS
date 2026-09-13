// OSIRIS API istemcisi — aynı-köken /api (nginx) veya dev proxy.

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  // API anahtarı öncelikli (rol sunucuda çözülür); JWT yedek.
  // (Eski oturumlardaki bayat viewer-JWT'nin admin anahtarını ezmesini önler.)
  const key = sessionStorage.getItem("osiris_key") ?? "";
  const jwt = sessionStorage.getItem("osiris_jwt") ?? "";
  if (key) return { "X-API-Key": key };
  if (jwt) return { Authorization: `Bearer ${jwt}` };
  return {};
}

const REQUEST_TIMEOUT_MS = 30000;

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      signal: ctrl.signal,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(init?.headers ?? {}),
      },
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "İstek zaman aşımına uğradı (30 sn)");
    }
    throw new ApiError(0, "Ağ hatası — sunucuya ulaşılamıyor");
  }
  clearTimeout(timer);
  if (res.status === 401) {
    sessionStorage.removeItem("osiris_key");
    sessionStorage.removeItem("osiris_jwt");
    sessionStorage.removeItem("osiris_role");
    throw new ApiError(401, "Oturum geçersiz — yeniden giriş yapın");
  }
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* düz metin gövde */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body: unknown) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });

export interface Stats {
  sources: number;
  sources_enabled: number;
  items: number;
  entities: number;
  edges: number;
  saved_queries: number;
  alerts: number;
  latest_item_at: string | null;
}

export interface Source {
  id: string;
  name: string;
  url: string | null;
  network_type: string;
  plugin_id: string;
  schedule: string | null;
  priority: number;
  enabled: boolean;
  tags: string[] | null;
  last_crawled_at: string | null;
  last_success_at: string | null;
  failure_count: number;
  avg_response_ms: number | null;
}

export interface Plugin {
  id: string;
  name: string;
  network_type: string;
  description: string;
  config_schema: Record<string, { type?: string; required?: boolean; default?: unknown; description?: string }>;
  schedule_default: string;
}

export interface SearchHit {
  id: string;
  title: string | null;
  url: string | null;
  cleaned_content?: string | null;
  snippet?: string | null;
  collected_at?: string | null;
}

export interface SavedQuery {
  id: string;
  name: string;
  query_text: string;
  query_type: string;
  alert_enabled: boolean;
  last_triggered_at: string | null;
}
