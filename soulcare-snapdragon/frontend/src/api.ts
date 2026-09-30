const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

interface ApiOptions extends Omit<RequestInit, "body"> {
  json?: unknown;
  body?: BodyInit | null;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem("soulcare_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let body = options.body ?? null;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }

  const { json: _json, ...rest } = options;
  const res = await fetch(apiUrl(path), { ...rest, headers, body });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const err = (await res.json()) as { detail?: string };
      detail = err.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export { API_BASE };
