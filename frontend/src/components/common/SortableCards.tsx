import { useEffect, useRef, useState } from "react";
import { GripVertical } from "lucide-react";
import { cn } from "@/lib/cn";

export interface SortableCardDef {
  node: React.ReactNode;
  /** In grid layout, how many columns this card spans (1 or 2). */
  colSpan?: number;
}

/** Move `from` next to `target`: before it when dragging up, after when down. */
function moveInArray(cur: string[], from: string, target: string): string[] {
  const fi = cur.indexOf(from);
  const ti = cur.indexOf(target);
  if (fi < 0 || ti < 0 || fi === ti) return cur;
  const next = [...cur];
  next.splice(fi, 1);
  next.splice(ti, 0, from);
  return next;
}

/**
 * Drag-to-reorder container. Persistence is the caller's job via `useCardOrder`.
 *
 * Implemented with raw pointer events rather than HTML5 drag-and-drop: the
 * Tauri WebView intercepts native drag events on Windows, so `dragstart`
 * never fires inside the desktop app.
 *
 * While dragging, the layout reorders LIVE under the pointer, so the dragged
 * card is always sitting exactly where it will land. Because that reorder
 * moves DOM nodes (which destroys pointer capture), the move/up/cancel
 * listeners live on `window` for the duration of the drag instead of relying
 * on capture. Esc cancels and reverts.
 */
export function SortableCards({
  cards,
  order,
  onReorder,
  layout = "stack",
  className,
}: {
  cards: Record<string, SortableCardDef>;
  order: string[];
  onReorder: (next: string[]) => void;
  layout?: "stack" | "grid";
  className?: string;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [preview, setPreview] = useState<string[] | null>(null);
  // Refs mirror the state so window listeners see current values without
  // re-binding mid-drag.
  const previewRef = useRef<string[] | null>(null);
  // Live listeners for the active drag, so unmount can detach them safely.
  const detachRef = useRef<(() => void) | null>(null);

  useEffect(() => () => detachRef.current?.(), []);

  function cardIdAt(x: number, y: number): string | null {
    for (const el of document.elementsFromPoint(x, y)) {
      const id = (el as HTMLElement).dataset?.cardId;
      if (id) return id;
    }
    return null;
  }

  function startDrag(e: React.PointerEvent, id: string) {
    // Left button / primary touch only; one drag at a time.
    if (e.button !== 0 || detachRef.current) return;
    e.preventDefault();
    previewRef.current = order;
    setDragId(id);
    setPreview(order);

    const onMove = (ev: PointerEvent) => {
      const target = cardIdAt(ev.clientX, ev.clientY);
      // Hovering the dragged card itself (its live drop slot) is a no-op,
      // which keeps the preview stable instead of oscillating after reflow.
      if (!target || target === id) return;
      const cur = previewRef.current ?? order;
      const next = moveInArray(cur, id, target);
      if (next !== cur) {
        previewRef.current = next;
        setPreview(next);
      }
    };
    const finish = (commit: boolean) => {
      detachRef.current?.();
      const next = previewRef.current;
      if (
        commit &&
        next &&
        (next.length !== order.length || next.some((v, i) => v !== order[i]))
      ) {
        onReorder(next);
      }
      previewRef.current = null;
      setDragId(null);
      setPreview(null);
    };
    const onUp = () => finish(true);
    const onCancel = () => finish(false);
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === "Escape") finish(false);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onCancel);
    window.addEventListener("keydown", onKey);
    detachRef.current = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onCancel);
      window.removeEventListener("keydown", onKey);
      detachRef.current = null;
    };
  }

  const shown = preview ?? order;

  return (
    <div
      className={cn(
        layout === "grid"
          ? "grid grid-cols-1 gap-4 lg:grid-cols-2 [grid-auto-flow:dense]"
          : "flex flex-col gap-4",
        dragId && "select-none",
        className,
      )}
    >
      {shown.map((id) => {
        const def = cards[id];
        if (!def) return null;
        const wide = layout === "grid" && (def.colSpan ?? 1) >= 2;
        const dragging = dragId === id;
        return (
          <div
            key={id}
            data-card-id={id}
            className={cn(
              "group relative rounded-lg",
              wide && "lg:col-span-2",
              // Lifted look while dragging. No ring-offset: it needs an offset
              // colour, and an invalid one silently kills the whole ring.
              dragging && "z-20 scale-[1.01] opacity-90 shadow-xl ring-2 ring-accent",
            )}
          >
            <button
              type="button"
              aria-label="Drag to reorder"
              title="Drag to reorder"
              onPointerDown={(e) => startDrag(e, id)}
              style={{ touchAction: "none" }}
              className={cn(
                "absolute right-1.5 top-1.5 z-10 rounded border bg-surface p-1 text-muted shadow-sm transition hover:text-ink",
                dragging
                  ? "cursor-grabbing opacity-100"
                  : "cursor-grab opacity-40 group-hover:opacity-100",
              )}
            >
              <GripVertical className="h-3.5 w-3.5" />
            </button>
            {def.node}
          </div>
        );
      })}
    </div>
  );
}
