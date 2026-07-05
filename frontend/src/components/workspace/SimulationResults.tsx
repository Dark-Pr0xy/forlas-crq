import { motion, AnimatePresence } from "motion/react";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { fmt } from "@/lib/format";
import { HistogramChart } from "@/components/workspace/charts/HistogramChart";
import { LecChart } from "@/components/workspace/charts/LecChart";
import { SensitivityTornado } from "@/components/workspace/charts/SensitivityTornado";
import {
  ReferenceLinesEditor,
  computeReferenceLines,
} from "@/components/workspace/ReferenceLinesEditor";
import type { ScenarioRead, SimulationResult } from "@/types/api";

interface SimulationResultsProps {
  scenario: ScenarioRead;
  simulation: SimulationResult | null | undefined;
  isLoading: boolean;
  error?: unknown;
  onScenarioChange: (patch: Partial<ScenarioRead>) => void;
}

export function SimulationResults({
  scenario,
  simulation,
  isLoading,
  error,
  onScenarioChange,
}: SimulationResultsProps) {
  if (isLoading) {
    return <p className="text-sm text-muted">Loading latest run…</p>;
  }
  if (!simulation || !simulation.statistics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No simulation yet</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-muted">
            Configure the inputs and click <span className="text-accent">Run simulation</span> to
            generate exposure metrics, the loss distribution, and a Loss Exceedance Curve.
          </p>
          {error != null && typeof error === "object" && "status" in error
            ? null
            : error != null && (
                <p className="mt-2 text-xs text-rose">Could not load runs from the backend.</p>
              )}
        </CardBody>
      </Card>
    );
  }

  const s = simulation.statistics;
  const refLines = computeReferenceLines(scenario, s);

  return (
    <div className="space-y-4">
      <AnimatePresence mode="popLayout">
        <motion.div
          key={simulation.id}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15 }}
          className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
        >
          <Kpi label="ALE (mean)" value={fmt.money(s.mean)} tone="accent" />
          <Kpi label="P50" value={fmt.money(s.p50)} tone="plum" />
          <Kpi label="P90" value={fmt.money(s.p90)} tone="teal" />
          <Kpi label="P95" value={fmt.money(s.p95)} tone="amber" />
          <Kpi label="P99" value={fmt.money(s.p99)} tone="rose" />
          <Kpi label="Tail mean (>P95)" value={fmt.money(s.tail_mean)} tone="rose" />
        </motion.div>
      </AnimatePresence>

      <ReferenceLinesEditor scenario={scenario} stats={s} onChange={onScenarioChange} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Loss distribution</CardTitle>
            <CardHint>{s.iterations.toLocaleString()} iterations · seed {s.seed}</CardHint>
          </CardHeader>
          <CardBody>
            {simulation.histogram ? (
              <HistogramChart histogram={simulation.histogram} referenceLines={refLines} />
            ) : (
              <p className="text-muted">Histogram unavailable.</p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Loss Exceedance Curve</CardTitle>
            <CardHint>P(L &gt; x) over empirical samples</CardHint>
          </CardHeader>
          <CardBody>
            {simulation.lec_curve ? (
              <LecChart curve={simulation.lec_curve} referenceLines={refLines} />
            ) : (
              <p className="text-muted">LEC unavailable.</p>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Sensitivity (rank correlation)</CardTitle>
            <CardHint>Drivers of total loss</CardHint>
          </CardHeader>
          <CardBody>
            {simulation.sensitivity?.length ? (
              <SensitivityTornado data={simulation.sensitivity} />
            ) : (
              <p className="text-muted">No sensitivity data.</p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tolerance metrics</CardTitle>
            <CardHint>From scenario tolerance {fmt.moneyFull(s.tolerance)}</CardHint>
          </CardHeader>
          <CardBody className="space-y-2.5">
            <Row label="P(Loss > Tolerance)" value={fmt.pct(s.prob_exceed_tolerance, 2)} />
            <Row label="Utilisation (mean / tolerance)" value={fmt.pct(s.tolerance_utilisation, 1)} />
            <Row
              label="Headroom (tolerance − mean)"
              value={fmt.moneyFull(s.difference_to_tolerance)}
            />
            <Row
              label="95% CI on mean"
              value={`${fmt.money(s.ci_lo)} … ${fmt.money(s.ci_hi)}`}
            />
            <Row
              label="Zero-loss iterations"
              value={`${s.zero_count.toLocaleString()} (${fmt.pct(
                s.zero_count / s.iterations,
                1,
              )})`}
            />
            <div className="pt-1">
              <Badge tone={s.tolerance_utilisation > 1 ? "rose" : "success"}>
                {s.tolerance_utilisation > 1
                  ? "Exceeds tolerance"
                  : "Within tolerance"}
              </Badge>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "accent" | "amber" | "plum" | "teal" | "rose";
}) {
  const strip = `bg-${tone}`;
  return (
    <Card className="relative overflow-hidden p-3.5">
      <div className={`kpi-strip ${strip}`} />
      <div className="pl-3">
        <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
        <div className="mt-1 text-[19px] font-semibold num">{value}</div>
      </div>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-[var(--c-border-2)] py-1.5 text-sm last:border-0">
      <span className="text-muted">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
