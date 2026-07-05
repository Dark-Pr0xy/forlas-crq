import { create } from "zustand";

/**
 * Theme is a per-user, client-side preference persisted to localStorage — not
 * the org-wide `app_settings.theme` (which is Owner-gated). This lets any user
 * pick light/dark without needing settings-write permission (M5).
 */

export type Theme = "light" | "dark";

const STORAGE_KEY = "forlas.theme";

function readInitial(): Theme {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function apply(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
}

export const useTheme = create<ThemeState>((set, get) => ({
  theme: "light",
  setTheme: (t) => {
    localStorage.setItem(STORAGE_KEY, t);
    apply(t);
    set({ theme: t });
  },
  toggle: () => get().setTheme(get().theme === "dark" ? "light" : "dark"),
}));

/** Call once at startup to apply the persisted/system theme before first paint. */
export function initTheme(): void {
  const t = readInitial();
  apply(t);
  useTheme.setState({ theme: t });
}
