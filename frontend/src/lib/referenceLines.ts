/**
 * Reference-line derivation shared by the editor card and the charts.
 * Kept out of the component file so fast refresh stays intact.
 */

import type { ReferenceLine, ScenarioRead, SimulationStatistics } from "@/types/api";

/** Toggleable percentile markers, in display order, with their colours. */
export const PERCENTILE_MARKERS: {
  key: keyof SimulationStatistics;
  label: string;
  color: string;
}[] = [
  { key: "p5", label: "P5", color: "#5AA0D8" },
  { key: "p50", label: "P50", color: "#78C5B7" },
  { key: "p90", label: "P90", color: "#7A92F4" },
  { key: "p95", label: "P95", color: "#D98DA3" },
  { key: "p99", label: "P99", color: "#E3C07B" },
];

export const TOLERANCE_COLOR = "#A28AD9";

/** Persisted toggle prefs. Defaults: P50, P95, Tolerance on. */
export interface RefToggles {
  p5?: boolean;
  p50?: boolean;
  p90?: boolean;
  p95?: boolean;
  p99?: boolean;
  tolerance?: boolean;
}

export const DEFAULT_TOGGLES: RefToggles = { p50: true, p95: true, tolerance: true };

/**
 * Compute the effective reference lines rendered on the histogram + LEC from
 * the toggle prefs, the scenario tolerance, and any custom lines.
 */
export function computeReferenceLines(
  scenario: ScenarioRead,
  stats: SimulationStatistics,
): ReferenceLine[] {
  const toggles: RefToggles = { ...DEFAULT_TOGGLES, ...(scenario.prefs?.refToggles as RefToggles) };
  const lines: ReferenceLine[] = [];
  for (const m of PERCENTILE_MARKERS) {
    if (toggles[m.key as keyof RefToggles]) {
      lines.push({ label: m.label, value: stats[m.key] as number, color: m.color });
    }
  }
  if (toggles.tolerance && scenario.tolerance > 0) {
    lines.push({ label: "Tolerance", value: scenario.tolerance, color: TOLERANCE_COLOR });
  }
  lines.push(...(scenario.reference_lines ?? []));
  return lines;
}
