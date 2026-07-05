import { useEffect, useState } from "react";
import { Camera, RotateCw } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { PortfolioLecChart } from "@/components/dashboard/PortfolioLecChart";
import { PortfolioTrendChart } from "@/components/dashboard/PortfolioTrendChart";
import { TopScenariosTable } from "@/components/dashboard/TopScenariosTable";
import { fmt } from "@/lib/format";
import {
  useCapturePortfolioSnapshot,
  usePortfolioRollup,
  usePortfolioSnapshots,
  useScenarios,
} from "@/lib/queries";

const APPETITE_KEY = "forlas.portfolio_appetite";

export function DashboardPage() {
  const qc = useQueryClient();
  const { data: scenarios } = useScenarios();
  // The rollup does NOT depend on appetite — the appetite line is drawn
  // client-side and utilisation is just ALE ÷ appetite. So we fetch the rollup
  // once (stable query key) and never refetch while typing an appetite.
  const { data: rollup, isLoading } = usePortfolioRollup();
  const { data: snapshots } = usePortfolioSnapshots();
  const snapshot = useCapturePortfolioSnapshot();

  // `appetiteInput` drives the text field (updates instantly, no side effects);
  // `appetite` is the debounced numeric value used for the chart line + badge.
  const [appetiteInput, setAppetiteInput] = useState<string>(() =>
    typeof localStorage !== "undefined" ? (localStorage.getItem(APPETITE_KEY) ?? "") : "",
  );
  const [appetite, setAppetite] = useState<number | null>(() => {
    if (typeof localStorage === "undefined") return null;
    const v = localStorage.getItem(APPETITE_KEY);
    return v ? Number(v) : null;
  });

  useEffect(() => {
    const t = setTimeout(() => {
      const raw = appetiteInput.trim();
      const v = raw ? Number(raw) : null;
      const next = v != null && Number.isFinite(v) ? v : null;
      setAppetite(next);
      if (next == null) localStorage.removeItem(APPETITE_KEY);
      else localStorage.setItem(APPETITE_KEY, String(next));
    }, 350);
    return () => clearTimeout(t);
  }, [appetiteInput]);

  const appetiteUtil =
    appetite != null && appetite > 0 && rollup ? rollup.total_ale / appetite : null;

  const awaitingSim =
    (scenarios?.length ?? 0) - (rollup?.simulated_count ?? 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Portfolio at a glance</h2>
          <p className="text-xs text-muted">
            Aggregated across {rollup?.simulated_count ?? 0} simulated scenario(s){" "}
            {rollup?.iterations
              ? `· ${rollup.iterations.toLocaleString()} iterations`
              : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => {
              qc.invalidateQueries({ queryKey: ["portfolio", "rollup"] });
              qc.invalidateQueries({ queryKey: ["portfolio", "register"] });
              qc.invalidateQueries({ queryKey: ["scenarios"] });
            }}
          >
            <RotateCw className="h-4 w-4" />
            Refresh
          </Button>
          <Button
            onClick={() =>
              snapshot.mutate({ reason: "manual" })
            }
            disabled={snapshot.isPending || !(rollup && rollup.simulated_count > 0)}
          >
            <Camera className="h-4 w-4" />
            {snapshot.isPending ? "Capturing…" : "Capture snapshot"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        <Kpi label="Portfolio ALE" value={fmt.money(rollup?.total_ale ?? 0)} tone="accent" sub={isLoading ? "Loading…" : undefined} />
        <Kpi label="P50" value={fmt.money(rollup?.total_p50 ?? 0)} tone="plum" />
        <Kpi label="P90" value={fmt.money(rollup?.total_p90 ?? 0)} tone="teal" />
        <Kpi label="P95" value={fmt.money(rollup?.total_p95 ?? 0)} tone="amber" />
        <Kpi label="P99" value={fmt.money(rollup?.total_p99 ?? 0)} tone="rose" />
        <Kpi label="Tail mean" value={fmt.money(rollup?.total_tail ?? 0)} tone="rose" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Loss Exceedance</CardTitle>
            <CardHint>P(total annual loss &gt; x)</CardHint>
          </CardHeader>
          <CardBody>
            <div className="mb-2 flex items-end justify-end gap-2">
              <div className="w-52">
                <Label className="text-[11px]">Risk appetite (AUD)</Label>
                <Input
                  type="number"
                  className="num"
                  placeholder="none"
                  value={appetiteInput}
                  onChange={(e) => setAppetiteInput(e.target.value)}
                />
              </div>
              {appetiteUtil != null && (
                <Badge tone={appetiteUtil > 1 ? "rose" : "success"} className="mb-1.5">
                  mean {fmt.pct(appetiteUtil)} of appetite
                </Badge>
              )}
            </div>
            {rollup && rollup.lec_curve.length > 0 ? (
              <PortfolioLecChart curve={rollup.lec_curve} appetite={appetite} />
            ) : (
              <p className="py-8 text-center text-sm text-muted">
                Run at least one simulation to see the aggregate LEC.
              </p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top loss drivers</CardTitle>
            <CardHint>Ranked by ALE</CardHint>
          </CardHeader>
          <CardBody>
            <TopScenariosTable rows={rollup?.top_scenarios ?? []} />
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Portfolio history</CardTitle>
          <CardHint>Captured snapshots — ALE / P95 / P99</CardHint>
        </CardHeader>
        <CardBody>
          <PortfolioTrendChart snapshots={snapshots ?? []} />
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Coverage</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold num">{rollup?.simulated_count ?? 0}</span>
              <span className="text-muted">/ {scenarios?.length ?? 0} scenarios simulated</span>
            </div>
            {awaitingSim > 0 && (
              <p className="mt-2 text-xs text-amber">
                {awaitingSim} scenario{awaitingSim === 1 ? "" : "s"} awaiting their first run.
              </p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Over tolerance</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold num">
                {rollup?.over_tolerance_count ?? 0}
              </span>
              <span className="text-muted">scenarios</span>
            </div>
            <p className="mt-2 text-xs text-muted">
              Where mean loss exceeds the configured tolerance.
            </p>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Confidence interval</CardTitle>
            <CardHint>95% CI on portfolio mean</CardHint>
          </CardHeader>
          <CardBody>
            <div className="font-mono">
              {rollup ? `${fmt.money(rollup.ci_lo)} … ${fmt.money(rollup.ci_hi)}` : "—"}
            </div>
            <Badge tone="neutral" className="mt-2">
              {rollup?.iterations ? `n = ${rollup.iterations.toLocaleString()}` : "—"}
            </Badge>
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
  sub,
}: {
  label: string;
  value: string;
  tone: "accent" | "amber" | "plum" | "teal" | "rose";
  sub?: string;
}) {
  const strip = `bg-${tone}`;
  return (
    <Card className="relative overflow-hidden p-3.5">
      <div className={`kpi-strip ${strip}`} />
      <div className="pl-3">
        <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
        <div className="mt-1 text-[20px] font-semibold num">{value}</div>
        {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
      </div>
    </Card>
  );
}
