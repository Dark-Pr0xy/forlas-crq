import { useState } from "react";
import { Plus, X } from "lucide-react";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { fmt } from "@/lib/format";
import {
  DEFAULT_TOGGLES,
  PERCENTILE_MARKERS,
  TOLERANCE_COLOR,
  type RefToggles,
} from "@/lib/referenceLines";
import type { ReferenceLine, ScenarioRead, SimulationStatistics } from "@/types/api";

interface ReferenceLinesEditorProps {
  scenario: ScenarioRead;
  stats: SimulationStatistics;
  onChange: (patch: Partial<ScenarioRead>) => void;
}

export function ReferenceLinesEditor({ scenario, stats, onChange }: ReferenceLinesEditorProps) {
  const toggles: RefToggles = { ...DEFAULT_TOGGLES, ...(scenario.prefs?.refToggles as RefToggles) };
  const customLines = scenario.reference_lines ?? [];

  function setToggle(key: keyof RefToggles, on: boolean) {
    onChange({
      prefs: { ...(scenario.prefs ?? {}), refToggles: { ...toggles, [key]: on } },
    });
  }

  function updateCustom(next: ReferenceLine[]) {
    onChange({ reference_lines: next });
  }

  function addCustom(label: string, value: number, color: string) {
    updateCustom([...customLines, { label, value, color }]);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reference lines</CardTitle>
        <CardHint>Shown on histogram &amp; LEC</CardHint>
      </CardHeader>
      <CardBody className="space-y-3">
        {/* Percentile + tolerance toggles */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          {PERCENTILE_MARKERS.map((m) => (
            <label key={m.key} className="flex cursor-pointer items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={!!toggles[m.key as keyof RefToggles]}
                onChange={(e) => setToggle(m.key as keyof RefToggles, e.target.checked)}
                className="accent-[#7A92F4]"
              />
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ background: m.color }}
              />
              {m.label}
            </label>
          ))}
          <label className="flex cursor-pointer items-center gap-1.5 text-sm">
            <input
              type="checkbox"
              checked={!!toggles.tolerance}
              onChange={(e) => setToggle("tolerance", e.target.checked)}
              className="accent-[#7A92F4]"
            />
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: TOLERANCE_COLOR }}
            />
            Tolerance
          </label>
        </div>

        {/* Existing custom lines */}
        {customLines.map((line, i) => (
          <CustomLineRow
            key={i}
            line={line}
            onChange={(next) =>
              updateCustom(customLines.map((l, j) => (j === i ? next : l)))
            }
            onRemove={() => updateCustom(customLines.filter((_, j) => j !== i))}
          />
        ))}

        {/* Preset add buttons */}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => addCustom("Insurance retention", Math.round(stats.p50), "#8CC5A0")}
          >
            <Plus className="h-3.5 w-3.5" /> Insurance retention
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => addCustom("Insurance limit", Math.round(stats.p95), "#78C5B7")}
          >
            <Plus className="h-3.5 w-3.5" /> Insurance limit
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => addCustom("Capital reserve", Math.round(stats.p99), "#E3C07B")}
          >
            <Plus className="h-3.5 w-3.5" /> Capital reserve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => addCustom("Custom marker", Math.round(stats.mean), "#7A92F4")}
          >
            <Plus className="h-3.5 w-3.5" /> Custom
          </Button>
        </div>

        <p className="text-[11px] text-muted">
          Lines render on both Loss Distribution and Loss Exceedance charts.
        </p>
      </CardBody>
    </Card>
  );
}

function CustomLineRow({
  line,
  onChange,
  onRemove,
}: {
  line: ReferenceLine;
  onChange: (next: ReferenceLine) => void;
  onRemove: () => void;
}) {
  const [label, setLabel] = useState(line.label);
  const [value, setValue] = useState(String(line.value));

  return (
    <div className="flex items-center gap-2">
      <Input
        value={label}
        onChange={(e) => {
          setLabel(e.target.value);
          onChange({ ...line, label: e.target.value });
        }}
        className="flex-1"
      />
      <Input
        type="number"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          const n = Number(e.target.value);
          if (Number.isFinite(n)) onChange({ ...line, value: n });
        }}
        className="w-[180px]"
        title={fmt.money(line.value)}
      />
      <input
        type="color"
        value={line.color}
        onChange={(e) => onChange({ ...line, color: e.target.value })}
        className="h-8 w-9 cursor-pointer rounded border bg-surface p-0.5"
        aria-label="Line colour"
      />
      <Button size="icon" variant="ghost" onClick={onRemove} title="Remove line">
        <X className="h-4 w-4" />
      </Button>
    </div>
  );
}
