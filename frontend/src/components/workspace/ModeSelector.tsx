import { cn } from "@/lib/cn";
import type { DecompositionMode } from "@/types/api";

const MODES: { id: DecompositionMode; label: string; hint: string }[] = [
  {
    id: "lef",
    label: "Direct LEF",
    hint: "Estimate Loss Event Frequency directly. Use when you have historical event data.",
  },
  {
    id: "tef-vuln",
    label: "TEF × Vulnerability",
    hint: "Default approach. Estimate Threat Event Frequency and Vulnerability independently.",
  },
  {
    id: "full",
    label: "Full decomposition",
    hint: "Decompose Vulnerability into Threat Capability vs Resistance Strength.",
  },
];

interface ModeSelectorProps {
  value: DecompositionMode;
  onChange: (mode: DecompositionMode) => void;
  disabled?: boolean;
}

export function ModeSelector({ value, onChange, disabled }: ModeSelectorProps) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">
        Decomposition mode
      </div>
      <div className="grid grid-cols-1 gap-1.5">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            disabled={disabled}
            onClick={() => onChange(m.id)}
            className={cn(
              "flex flex-col items-start gap-0.5 rounded-sm border px-2.5 py-2 text-left transition",
              value === m.id
                ? "border-accent bg-accent-soft"
                : "bg-surface hover:bg-[var(--c-border-2)]",
              disabled && "opacity-50",
            )}
          >
            <div className="text-sm font-medium text-ink">{m.label}</div>
            <div className="text-[11px] leading-snug text-muted">{m.hint}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
