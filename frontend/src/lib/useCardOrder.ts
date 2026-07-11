import { useCallback, useState } from "react";

/**
 * Persisted, user-customisable card ordering.
 *
 * The order lives in localStorage (per machine/browser — no backend), and is
 * reconciled against the current default on load so that cards added or removed
 * in a later app version still appear (new ones appended, missing ones dropped)
 * without wiping the user's arrangement.
 *
 * Pass a STABLE `defaultOrder` reference (a module-level constant) so `reset`
 * and identity checks behave.
 */
function reconcile(saved: string[], def: string[]): string[] {
  const known = new Set(def);
  const merged = saved.filter((id) => known.has(id));
  for (const id of def) if (!merged.includes(id)) merged.push(id);
  return merged;
}

export function useCardOrder(storageKey: string, defaultOrder: string[]) {
  const [order, setOrder] = useState<string[]>(() => {
    if (typeof localStorage === "undefined") return defaultOrder;
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return defaultOrder;
      const saved = JSON.parse(raw);
      if (!Array.isArray(saved)) return defaultOrder;
      return reconcile(
        saved.filter((x): x is string => typeof x === "string"),
        defaultOrder,
      );
    } catch {
      return defaultOrder;
    }
  });

  const apply = useCallback(
    (next: string[]) => {
      try {
        localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        /* storage unavailable — order still works in-session */
      }
      setOrder(next);
    },
    [storageKey],
  );

  const reset = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
    } catch {
      /* ignore */
    }
    setOrder(defaultOrder);
  }, [storageKey, defaultOrder]);

  const isCustomized =
    order.length !== defaultOrder.length || order.some((v, i) => v !== defaultOrder[i]);

  return { order, apply, reset, isCustomized };
}
