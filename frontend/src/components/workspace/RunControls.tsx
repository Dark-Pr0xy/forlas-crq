import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Slider } from "@/components/ui/Slider";
import { fmt } from "@/lib/format";
import { apiErrorMessage } from "@/lib/api";
import { useRunSimulation } from "@/lib/queries";
import type { AppSettings, ScenarioRead } from "@/types/api";

interface RunControlsProps {
  scenario: ScenarioRead;
  settings: AppSettings;
  onReductionChange: (pct: number) => void;
  isDirty: boolean;
  problems?: string[];
  onSaveBeforeRun: () => Promise<void>;
}

export function RunControls({
  scenario,
  settings,
  onReductionChange,
  isDirty,
  problems = [],
  onSaveBeforeRun,
}: RunControlsProps) {
  const [iterations, setIterations] = useState<number>(settings.iterations);
  const [seed, setSeed] = useState<number>(settings.seed);
  const [runError, setRunError] = useState<string | null>(null);
  const runMutation = useRunSimulation(scenario.id);
  const blocked = problems.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label>Iterations</Label>
            <Input
              type="number"
              value={iterations}
              min={1_000}
              max={5_000_000}
              step={1_000}
              onChange={(e) => setIterations(Number(e.target.value))}
            />
          </div>
          <div className="space-y-1">
            <Label>Seed</Label>
            <Input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <Label>What-if control reduction</Label>
            <span className="text-xs text-muted font-mono">
              {scenario.reduction_pct}%
            </span>
          </div>
          <Slider
            min={0}
            max={90}
            step={5}
            value={scenario.reduction_pct}
            onValueChange={onReductionChange}
          />
        </div>

        <Button
          className="w-full"
          disabled={runMutation.isPending || blocked}
          title={blocked ? "Resolve the highlighted issues first" : undefined}
          onClick={async () => {
            setRunError(null);
            try {
              // Save first (server runs off the saved scenario). If the save
              // is rejected — validation, lock, permission — surface why and
              // don't pretend to run.
              if (isDirty) await onSaveBeforeRun();
              await runMutation.mutateAsync({
                iterations,
                seed,
                persist_artifacts: true,
              });
            } catch (e) {
              setRunError(apiErrorMessage(e));
            }
          }}
        >
          {runMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Simulating…
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run simulation
            </>
          )}
        </Button>
        {blocked && (
          <p className="text-[11px] text-amber">
            {problems.length} issue{problems.length === 1 ? "" : "s"} to fix before running —
            see the highlighted panel.
          </p>
        )}
        {runError && (
          <div className="rounded border border-rose px-2.5 py-2 text-[11px] text-rose">
            <span className="font-semibold">Couldn&apos;t run:</span> {runError}
          </div>
        )}
        {runMutation.data?.statistics && (
          <p className="text-[11px] text-muted">
            Last run · ALE {fmt.money(runMutation.data.statistics.mean)} · P95{" "}
            {fmt.money(runMutation.data.statistics.p95)}
          </p>
        )}
      </CardBody>
    </Card>
  );
}
