import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import { usePortfolioRollup } from "@/lib/queries";
import type { SimulationResult } from "@/types/api";

interface PresentationModeProps {
  scenarioIds: string[];
  onClose: () => void;
}

/** Full-screen slide deck — title slide, portfolio aggregate, then one slide per scenario. */
export function PresentationMode({ scenarioIds, onClose }: PresentationModeProps) {
  const [slide, setSlide] = useState(0);
  // Portfolio slide must reflect the SAME scenario selection as the per-scenario
  // slides, otherwise the aggregate totals contradict the detail (M1).
  const { data: rollup } = usePortfolioRollup(null, scenarioIds);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" || e.key === " ") setSlide((n) => n + 1);
      if (e.key === "ArrowLeft") setSlide((n) => Math.max(0, n - 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const totalSlides = 2 + scenarioIds.length; // title + portfolio + N scenarios
  const clamped = Math.max(0, Math.min(slide, totalSlides - 1));
  const slideKind: "title" | "portfolio" | "scenario" =
    clamped === 0 ? "title" : clamped === 1 ? "portfolio" : "scenario";
  const scenarioId = slideKind === "scenario" ? scenarioIds[clamped - 2] : null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#0e1320] text-white">
      <div className="flex items-center justify-between border-b border-white/10 px-6 py-3">
        <div className="text-xs uppercase tracking-wider text-white/50">
          FORLAS CRQ · Presentation
        </div>
        <div className="text-xs text-white/40">
          Slide {clamped + 1} of {totalSlides} · ← → to navigate · Esc to close
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-white/60 hover:bg-white/10 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="flex flex-1 items-center justify-center px-12">
        {slideKind === "title" && <TitleSlide rollup={rollup} />}
        {slideKind === "portfolio" && <PortfolioSlide rollup={rollup} />}
        {slideKind === "scenario" && scenarioId && <ScenarioSlide id={scenarioId} />}
      </div>
      <div className="flex items-center justify-between px-6 py-4">
        <button
          onClick={() => setSlide((n) => Math.max(0, n - 1))}
          className="rounded border border-white/15 px-3 py-1.5 text-sm text-white/70 hover:bg-white/10"
          disabled={clamped === 0}
        >
          <ChevronLeft className="inline h-4 w-4" /> Prev
        </button>
        <button
          onClick={() => setSlide((n) => Math.min(totalSlides - 1, n + 1))}
          className="rounded border border-white/15 px-3 py-1.5 text-sm text-white/70 hover:bg-white/10"
          disabled={clamped === totalSlides - 1}
        >
          Next <ChevronRight className="inline h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function TitleSlide({ rollup }: { rollup: ReturnType<typeof usePortfolioRollup>["data"] }) {
  return (
    <div className="text-center">
      <div className="text-xs uppercase tracking-[0.4em] text-white/50">
        Cyber Risk Quantification
      </div>
      <h1 className="mt-3 text-5xl font-semibold tracking-tight">
        Portfolio Exposure
      </h1>
      <p className="mt-6 text-white/60">
        Aggregated across {rollup?.simulated_count ?? 0} simulated scenarios · ALE{" "}
        <span className="font-mono text-white">{fmt.money(rollup?.total_ale ?? 0)}</span>
      </p>
    </div>
  );
}

function PortfolioSlide({
  rollup,
}: {
  rollup: ReturnType<typeof usePortfolioRollup>["data"];
}) {
  if (!rollup) return <p className="text-white/50">No portfolio data.</p>;
  return (
    <div className="w-full max-w-[1000px]">
      <h2 className="text-xs uppercase tracking-[0.3em] text-white/40">
        Portfolio at a glance
      </h2>
      <div className="mt-4 grid grid-cols-3 gap-5">
        <SlideKpi label="ALE" value={fmt.money(rollup.total_ale)} />
        <SlideKpi label="P95" value={fmt.money(rollup.total_p95)} />
        <SlideKpi label="P99" value={fmt.money(rollup.total_p99)} />
        <SlideKpi label="Tail mean" value={fmt.money(rollup.total_tail)} />
        <SlideKpi label="Over tolerance" value={`${rollup.over_tolerance_count}`} />
        <SlideKpi
          label="95% CI"
          value={`${fmt.money(rollup.ci_lo)} … ${fmt.money(rollup.ci_hi)}`}
          small
        />
      </div>
      <div className="mt-8">
        <h3 className="text-xs uppercase tracking-wider text-white/40">Top drivers</h3>
        <ul className="mt-3 space-y-1.5 text-sm">
          {rollup.top_scenarios.slice(0, 5).map((s) => (
            <li
              key={s.scenario_id}
              className="flex items-baseline justify-between border-b border-white/5 pb-1.5"
            >
              <span>{s.name}</span>
              <span className="font-mono text-white/70">
                {fmt.money(s.ale)} · {fmt.pct(s.share_of_ale, 0)} share
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ScenarioSlide({ id }: { id: string }) {
  const { data: scn } = useQuery({
    queryKey: ["scenarios", id, "presentation"],
    queryFn: () => api.get<import("@/types/api").ScenarioRead>(`/api/scenarios/${id}`),
  });
  const { data: sim } = useQuery({
    queryKey: ["scenarios", id, "presentation", "sim"],
    queryFn: () =>
      api.get<SimulationResult>(`/api/scenarios/${id}/simulations/latest`).catch(() => null),
  });

  if (!scn) return <p className="text-white/50">Loading…</p>;

  const s = sim?.statistics;
  return (
    <div className="w-full max-w-[1000px]">
      <div className="text-xs uppercase tracking-[0.3em] text-white/40">Scenario</div>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight">{scn.name}</h2>
      <p className="mt-2 text-sm text-white/50">
        {scn.business_unit ?? "—"} · {scn.scenario_type ?? "—"} · v{scn.version_label}
      </p>
      {s ? (
        <div className="mt-6 grid grid-cols-4 gap-5">
          <SlideKpi label="ALE" value={fmt.money(s.mean)} />
          <SlideKpi label="P95" value={fmt.money(s.p95)} />
          <SlideKpi label="P99" value={fmt.money(s.p99)} />
          <SlideKpi label="Tolerance" value={fmt.money(s.tolerance)} />
        </div>
      ) : (
        <p className="mt-6 text-white/50">No simulation run yet.</p>
      )}
      {sim?.sensitivity && sim.sensitivity.length > 0 && (
        <div className="mt-8">
          <h3 className="text-xs uppercase tracking-wider text-white/40">Top drivers</h3>
          <ul className="mt-3 space-y-1 text-sm">
            {sim.sensitivity.slice(0, 4).map((d) => (
              <li
                key={d.name}
                className="flex items-baseline justify-between border-b border-white/5 pb-1"
              >
                <span>{d.label}</span>
                <span className="font-mono text-white/70">{d.corr.toFixed(3)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SlideKpi({ label, value, small }: { label: string; value: string; small?: boolean }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-5 py-4">
      <div className="text-[10px] uppercase tracking-wider text-white/40">{label}</div>
      <div
        className={`mt-1 font-semibold font-mono ${small ? "text-lg" : "text-3xl"}`}
      >
        {value}
      </div>
    </div>
  );
}
