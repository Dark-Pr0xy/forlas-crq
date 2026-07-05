import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/Badge";
import { fmt } from "@/lib/format";
import type { TopScenarioEntry } from "@/types/api";

export function TopScenariosTable({ rows }: { rows: TopScenarioEntry[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted">No simulated scenarios yet.</p>;
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-xs uppercase tracking-wide text-muted">
          <th className="py-2 pr-2">Scenario</th>
          <th className="py-2 pr-2 text-right">ALE</th>
          <th className="py-2 pr-2 text-right">P95</th>
          <th className="py-2 pr-2 text-right">Share</th>
          <th className="py-2 pr-2 text-right">Utilisation</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.scenario_id} className="border-b border-[var(--c-border-2)]">
            <td className="py-2 pr-2">
              <Link
                to="/workspace"
                className="font-medium text-ink hover:text-accent"
                title="Open in Workspace"
              >
                {r.name}
              </Link>
            </td>
            <td className="py-2 pr-2 text-right font-mono">{fmt.money(r.ale)}</td>
            <td className="py-2 pr-2 text-right font-mono">{fmt.money(r.p95)}</td>
            <td className="py-2 pr-2 text-right font-mono">{fmt.pct(r.share_of_ale, 1)}</td>
            <td className="py-2 pr-2 text-right">
              {r.tolerance > 0 ? (
                <Badge tone={r.over_tolerance ? "rose" : "success"}>
                  {fmt.pct(r.utilisation, 0)}
                </Badge>
              ) : (
                <span className="text-muted">—</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
