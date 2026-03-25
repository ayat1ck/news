const ENV_API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim() || '';

export function getApiBase() {
  if (ENV_API_BASE) return ENV_API_BASE;
  if (typeof window !== 'undefined') {
    const { protocol, hostname, origin } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }
    if (protocol === 'http:' || protocol === 'https:') {
      return origin;
    }
  }
  return '';
}

type FetchOptions = {
  method?: string;
  body?: unknown;
  token?: string;
};

export async function apiFetch<T = unknown>(path: string, opts: FetchOptions = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (opts.token) headers['Authorization'] = `Bearer ${opts.token}`;

  const apiBase = getApiBase();
  const url = apiBase ? `${apiBase}${path}` : path;

  const res = await fetch(url, {
    method: opts.method || 'GET',
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API error');
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
