/**
 * Thin typed `fetch` wrapper.
 *
 * Two runtime modes:
 *  - Browser (dev via Vite proxy, or Docker same-origin): relative `/api` URLs,
 *    cookie auth.
 *  - Tauri desktop: the WebView origin (tauri://localhost) is cross-origin to
 *    the backend, so we target the absolute backend URL and authenticate with
 *    the `X-Session-Token` header instead of a cookie (SameSite cookies aren't
 *    sent cross-origin).
 */

const IS_TAURI =
  typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
const API_BASE = IS_TAURI ? "http://127.0.0.1:8765" : "";
const TOKEN_STORAGE_KEY = "forlas.session_token";

let sessionToken: string | null =
  typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_STORAGE_KEY) : null;

export function setSessionToken(token: string | null): void {
  sessionToken = token;
  if (typeof localStorage !== "undefined") {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Turn any thrown error — especially an `ApiError` — into a human-readable
 * sentence. Handles FastAPI's three detail shapes: a plain string, an object
 * with a `detail` string, and a 422 validation array of `{loc, msg}`.
 */
export function apiErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const d = err.detail as unknown;
    if (typeof d === "string") return d;
    if (d && typeof d === "object") {
      const detail = (d as { detail?: unknown }).detail ?? d;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((e) => {
            const loc = Array.isArray(e?.loc)
              ? e.loc.filter((x: unknown) => x !== "body").join(" → ")
              : "";
            const msg = e?.msg ?? String(e);
            return loc ? `${loc}: ${msg}` : msg;
          })
          .join("; ");
      }
    }
    return err.message || `HTTP ${err.status}`;
  }
  if (err instanceof Error) return err.message;
  return "Unexpected error";
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface RequestOptions {
  method?: Method;
  body?: unknown;
  signal?: AbortSignal;
  // For multipart uploads, pass a FormData and we'll skip JSON serialisation.
  formData?: FormData;
}

/**
 * Global 401 handler. Registered by App so a lazy import cycle
 * (api → store → …) is avoided. When any request comes back 401 — expired
 * session, backend restart, revoked token — we clear auth state so the app
 * falls back to the login panel instead of silently showing empty screens.
 */
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

async function request<T = unknown>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (sessionToken) headers["X-Session-Token"] = sessionToken;

  const init: RequestInit = {
    method: opts.method ?? "GET",
    credentials: "include",
    signal: opts.signal,
    headers,
  };
  if (opts.formData) {
    init.body = opts.formData;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }

  const res = await fetch(`${API_BASE}${path}`, init);
  const contentType = res.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await res.json().catch(() => null) : await res.text();

  if (!res.ok) {
    // A 401 on anything other than the session probe means the session died
    // mid-use; kick the app back to the login panel.
    if (res.status === 401 && !path.endsWith("/api/auth/session") && onUnauthorized) {
      onUnauthorized();
    }
    throw new ApiError(res.status, payload);
  }
  return payload as T;
}

export const api = {
  get: <T = unknown>(path: string, signal?: AbortSignal) =>
    request<T>(path, { method: "GET", signal }),
  post: <T = unknown>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", body, signal }),
  patch: <T = unknown>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "PATCH", body, signal }),
  delete: <T = unknown>(path: string, signal?: AbortSignal) =>
    request<T>(path, { method: "DELETE", signal }),
  upload: <T = unknown>(path: string, file: File, signal?: AbortSignal) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<T>(path, { method: "POST", formData: fd, signal });
  },

  /**
   * Fetch a binary/text response as a Blob, honouring API_BASE + the session
   * token. Use for file downloads and report generation — a raw `fetch` or
   * anchor `href` with a relative URL breaks in the Tauri WebView (wrong
   * origin, no auth header).
   */
  async blob(
    path: string,
    opts: { method?: Method; body?: unknown } = {},
  ): Promise<Blob> {
    const headers: Record<string, string> = {};
    if (sessionToken) headers["X-Session-Token"] = sessionToken;
    const init: RequestInit = {
      method: opts.method ?? "GET",
      credentials: "include",
      headers,
    };
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
    }
    const res = await fetch(`${API_BASE}${path}`, init);
    if (!res.ok) {
      if (res.status === 401 && onUnauthorized) onUnauthorized();
      throw new ApiError(res.status, await res.text().catch(() => null));
    }
    return res.blob();
  },

  /** As `blob`, but returns text (for HTML report preview). */
  async text(
    path: string,
    opts: { method?: Method; body?: unknown } = {},
  ): Promise<string> {
    const b = await api.blob(path, opts);
    return b.text();
  },
};

/** Trigger a browser download for a Blob. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 200);
}
