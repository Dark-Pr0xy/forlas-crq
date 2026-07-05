import { useMemo } from "react";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { cn } from "@/lib/cn";
import type { DistributionParam, DistributionType } from "@/types/api";

const TYPE_OPTIONS: { value: DistributionType; label: string }[] = [
  { value: "pert", label: "PERT" },
  { value: "triangular", label: "Triangular" },
  { value: "uniform", label: "Uniform" },
  { value: "normal", label: "Normal" },
  { value: "lognormal", label: "Lognormal (10/90)" },
  { value: "beta", label: "Beta" },
  { value: "gamma", label: "Gamma" },
];

const NEEDS_MODE: DistributionType[] = ["pert", "triangular"];
const NEEDS_MIN_MAX: DistributionType[] = [
  "pert",
  "triangular",
  "uniform",
  "normal",
  "lognormal",
  "beta",
  "gamma",
];

interface DistributionParamCardProps {
  title: string;
  unit?: string;
  hint?: string;
  value: DistributionParam | undefined;
  onChange: (next: DistributionParam) => void;
  disabled?: boolean;
}

export function DistributionParamCard({
  title,
  unit,
  hint,
  value,
  onChange,
  disabled,
}: DistributionParamCardProps) {
  const v = value ?? ({ type: "pert" } as DistributionParam);

  const preview = useMemo(() => previewLine(v), [v]);

  function update<K extends keyof DistributionParam>(key: K, next: DistributionParam[K]) {
    onChange({ ...v, [key]: next });
  }

  return (
    <div className="rounded border bg-surface p-3">
      <div className="flex items-center gap-2">
        <div className="text-sm font-semibold text-ink">{title}</div>
        {unit && <span className="rounded-full bg-[var(--c-border-2)] px-2 py-0.5 text-[10px] text-muted">{unit}</span>}
        <div className="ml-auto w-28">
          <Select
            value={v.type}
            disabled={disabled}
            onChange={(e) => onChange({ type: e.target.value as DistributionType, min: v.min, mode: v.mode, max: v.max })}
            aria-label={`${title} distribution type`}
          >
            {TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {hint && <div className="mt-1 text-[11px] text-muted">{hint}</div>}

      <div className={cn("mt-2 grid gap-1.5", paramGridCols(v.type))}>
        {NEEDS_MIN_MAX.includes(v.type) && (
          <NumberInput
            label={v.type === "lognormal" ? "P10" : "Min"}
            value={v.min ?? 0}
            onChange={(n) => update("min", n)}
            disabled={disabled}
          />
        )}
        {NEEDS_MODE.includes(v.type) && (
          <NumberInput
            label="Mode"
            value={v.mode ?? 0}
            onChange={(n) => update("mode", n)}
            disabled={disabled}
          />
        )}
        {NEEDS_MIN_MAX.includes(v.type) && (
          <NumberInput
            label={v.type === "lognormal" ? "P90" : "Max"}
            value={v.max ?? 0}
            onChange={(n) => update("max", n)}
            disabled={disabled}
          />
        )}
        {v.type === "beta" && (
          <>
            <NumberInput
              label="Alpha"
              value={v.alpha ?? 2}
              onChange={(n) => update("alpha", n)}
              disabled={disabled}
            />
            <NumberInput
              label="Beta"
              value={v.beta ?? 5}
              onChange={(n) => update("beta", n)}
              disabled={disabled}
            />
          </>
        )}
        {v.type === "gamma" && (
          <NumberInput
            label="Shape"
            value={v.shape ?? 2}
            onChange={(n) => update("shape", n)}
            disabled={disabled}
          />
        )}
      </div>

      <div className="mt-2 text-[11px] text-muted font-mono">{preview}</div>
    </div>
  );
}

function paramGridCols(type: DistributionType): string {
  if (NEEDS_MODE.includes(type)) return "grid-cols-3";
  if (type === "beta") return "grid-cols-4";
  return "grid-cols-2";
}

function NumberInput({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <Input
        type="number"
        value={Number.isFinite(value) ? value : ""}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
      />
    </label>
  );
}

function previewLine(p: DistributionParam): string {
  switch (p.type) {
    case "pert": {
      const mean = p.min != null && p.mode != null && p.max != null
        ? (p.min + 4 * p.mode + p.max) / 6
        : null;
      return `PERT(${p.min ?? "?"}, ${p.mode ?? "?"}, ${p.max ?? "?"}) · μ ≈ ${fmtSmall(mean)}`;
    }
    case "triangular":
      return `Triangular(${p.min ?? "?"}, ${p.mode ?? "?"}, ${p.max ?? "?"})`;
    case "uniform":
      return `Uniform(${p.min ?? "?"}, ${p.max ?? "?"})`;
    case "normal": {
      const mean = p.min != null && p.max != null ? (p.min + p.max) / 2 : null;
      const sd = p.min != null && p.max != null ? (p.max - p.min) / 6 : null;
      return `Normal(μ=${fmtSmall(mean)}, σ=${fmtSmall(sd)})`;
    }
    case "lognormal":
      return `Lognormal fit to P10=${p.min ?? "?"}, P90=${p.max ?? "?"}`;
    case "beta":
      return `Beta(α=${p.alpha}, β=${p.beta}) on [${p.min ?? 0}, ${p.max ?? 1}]`;
    case "gamma":
      return `Gamma(shape=${p.shape}, scale derived)`;
    default:
      return "";
  }
}

function fmtSmall(n: number | null | undefined): string {
  if (n == null || !Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1000) return n.toLocaleString();
  return n.toString();
}
