import { useState } from "react";
import { Copy, Plus, RotateCcw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import { fmt } from "@/lib/format";
import {
  useCloneScenario,
  useDeletedScenarios,
  useDeleteScenario,
  useRestoreScenario,
  useScenarios,
} from "@/lib/queries";
import type { ScenarioRead } from "@/types/api";

interface ScenarioListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreateNew: () => void;
}

export function ScenarioList({ selectedId, onSelect, onCreateNew }: ScenarioListProps) {
  const { data, isLoading } = useScenarios();
  const [filter, setFilter] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  const cloneMutation = useCloneScenario();
  const deleteMutation = useDeleteScenario();
  const restoreMutation = useRestoreScenario();
  const { data: deleted } = useDeletedScenarios(showDeleted);

  const filtered = (data ?? []).filter(
    (s) =>
      !filter ||
      s.name.toLowerCase().includes(filter.toLowerCase()) ||
      (s.business_unit ?? "").toLowerCase().includes(filter.toLowerCase()) ||
      (s.tags ?? []).some((t) => t.toLowerCase().includes(filter.toLowerCase())),
  );

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter scenarios…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <Button onClick={onCreateNew} size="icon" title="New scenario">
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 space-y-1 overflow-auto pr-1">
        {isLoading ? (
          <p className="text-xs text-muted">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-muted">No scenarios match.</p>
        ) : (
          filtered.map((s) => (
            <ScenarioCard
              key={s.id}
              scenario={s}
              active={s.id === selectedId}
              onSelect={() => onSelect(s.id)}
              onClone={async () => {
                const clone = await cloneMutation.mutateAsync(s.id);
                onSelect(clone.id);
              }}
              onDelete={async () => {
                if (
                  confirm(
                    `Delete "${s.name}"? You can restore it later from “Show deleted”.`,
                  )
                ) {
                  await deleteMutation.mutateAsync(s.id);
                  if (selectedId === s.id) onSelect("");
                }
              }}
            />
          ))
        )}

        {showDeleted && (deleted ?? []).length > 0 && (
          <div className="mt-3 border-t pt-2">
            <div className="mb-1 px-1 text-[10px] uppercase tracking-wide text-muted">
              Deleted
            </div>
            {(deleted ?? []).map((s) => (
              <div
                key={s.id}
                className="flex items-center gap-2 rounded-sm px-2.5 py-1.5 text-sm text-muted"
              >
                <span className="min-w-0 flex-1 truncate line-through">{s.name}</span>
                <Button
                  size="icon"
                  variant="ghost"
                  title="Restore"
                  onClick={() => restoreMutation.mutate(s.id)}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={() => setShowDeleted((v) => !v)}
        className="text-left text-[11px] text-muted hover:text-accent"
      >
        {showDeleted ? "Hide deleted" : "Show deleted"}
      </button>
    </div>
  );
}

function ScenarioCard({
  scenario,
  active,
  onSelect,
  onClone,
  onDelete,
}: {
  scenario: ScenarioRead;
  active: boolean;
  onSelect: () => void;
  onClone: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={cn(
        "group cursor-pointer rounded-sm border bg-surface p-2.5 transition hover:bg-[var(--c-border-2)]",
        active && "border-accent bg-accent-soft hover:bg-accent-soft",
      )}
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-ink">{scenario.name}</div>
          <div className="mt-0.5 truncate text-[11px] text-muted">
            {scenario.business_unit ?? "—"}
            {scenario.owner_label ? ` · ${scenario.owner_label}` : ""}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge tone="accent">{scenario.mode}</Badge>
            <Badge tone="neutral">tol {fmt.money(scenario.tolerance)}</Badge>
          </div>
        </div>
        <div className="flex flex-col gap-1 opacity-0 transition group-hover:opacity-100">
          <Button
            size="icon"
            variant="ghost"
            title="Clone"
            onClick={(e) => {
              e.stopPropagation();
              onClone();
            }}
          >
            <Copy className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            title="Delete"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
