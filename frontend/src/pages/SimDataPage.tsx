import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { Download } from "lucide-react";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { fmt } from "@/lib/format";
import { api, saveBlob } from "@/lib/api";
import {
  useLatestSimulation,
  useLosses,
  useScenarios,
} from "@/lib/queries";

interface IterationRow {
  iteration: number;
  loss: number;
  lef: number;
  percentile: number; // 0..1
  deltaFromMean: number; // signed AUD
  sigmaFromMean: number; // signed σ
}

export function SimDataPage() {
  const { data: scenarios } = useScenarios();
  const [selectedId, setSelectedId] = useState<string>("");
  const effective = selectedId || scenarios?.[0]?.id || "";
  const { data: latest } = useLatestSimulation(effective);
  const runId = latest?.id ?? null;
  const { data: losses, isLoading } = useLosses(runId);
  const totalIterations = losses?.total ?? latest?.iterations ?? 0;

  const stats = latest?.statistics ?? null;
  const mean = stats?.mean ?? 0;
  const std = stats?.std ?? 0;

  /**
   * Derive percentile, Δ from mean and σ from mean for each iteration.
   * The rank for percentiles comes from a sorted view of the loss vector
   * (built once via `argsort`), so the table can re-derive these for any
   * scenario without paying O(n log n) per row.
   */
  const rows: IterationRow[] = useMemo(() => {
    if (!losses) return [];
    const n = losses.losses.length;
    if (n === 0) return [];
    const idx = losses.losses
      .map((v, i) => [v, i] as [number, number])
      .sort((a, b) => a[0] - b[0]);
    const rank = new Float64Array(n);
    for (let r = 0; r < n; r++) rank[idx[r][1]] = r;
    const out: IterationRow[] = new Array(n);
    for (let i = 0; i < n; i++) {
      const loss = losses.losses[i];
      const delta = loss - mean;
      const sigma = std > 0 ? delta / std : 0;
      out[i] = {
        iteration: i + 1,
        loss,
        lef: losses.lefs[i] ?? 0,
        percentile: (rank[i] + 0.5) / n,
        deltaFromMean: delta,
        sigmaFromMean: sigma,
      };
    }
    return out;
  }, [losses, mean, std]);

  const [sorting, setSorting] = useState<SortingState>([{ id: "iteration", desc: false }]);

  const columns: ColumnDef<IterationRow>[] = useMemo(
    () => [
      {
        id: "iteration",
        header: "#",
        accessorKey: "iteration",
        cell: (c) => (
          <span className="font-mono text-xs">
            {c.getValue<number>().toLocaleString("en-AU")}
          </span>
        ),
      },
      {
        id: "loss",
        header: "Loss",
        accessorKey: "loss",
        cell: (c) => <span className="font-mono">{fmt.money(c.getValue<number>())}</span>,
      },
      {
        id: "lef",
        header: "LEF (events/year)",
        accessorKey: "lef",
        cell: (c) => <span className="font-mono">{c.getValue<number>().toFixed(4)}</span>,
      },
      {
        id: "percentile",
        header: "Percentile",
        accessorKey: "percentile",
        cell: (c) => <span className="font-mono">{fmt.pct(c.getValue<number>(), 2)}</span>,
      },
      {
        id: "deltaFromMean",
        header: "Δ from mean",
        accessorKey: "deltaFromMean",
        cell: ({ getValue }) => (
          <span
            className={`font-mono ${
              getValue<number>() >= 0 ? "text-ink" : "text-rose"
            }`}
          >
            {fmt.signedMoney(getValue<number>())}
          </span>
        ),
      },
      {
        id: "sigmaFromMean",
        header: "σ from mean",
        accessorKey: "sigmaFromMean",
        cell: ({ getValue }) => (
          <span
            className={`font-mono ${
              Math.abs(getValue<number>()) >= 2 ? "text-rose" : "text-muted"
            }`}
          >
            {fmt.sigma(getValue<number>())}
          </span>
        ),
      },
    ],
    [],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  // Hard-cap DOM rendering for very long runs; full vector is still exportable.
  const visibleRows = table.getRowModel().rows.slice(0, 2000);

  async function downloadCsv() {
    if (!runId) return;
    // Fetch the full-vector CSV through the token-aware client (a plain anchor
    // href would miss the auth header + backend origin in the desktop app).
    const blob = await api.blob(`/api/simulations/${runId}/losses.csv`);
    saveBlob(blob, `simulation_${runId}.csv`);
  }

  function downloadJson() {
    if (!rows.length) return;
    const json = JSON.stringify(
      { run_id: runId, statistics: latest?.statistics, preview_rows: rows },
      null,
      2,
    );
    saveBlob(new Blob([json], { type: "application/json" }), `simulation_${runId}_preview.json`);
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Simulation data</CardTitle>
          <CardHint>{totalIterations.toLocaleString("en-AU")} iterations</CardHint>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-[320px]">
              <div className="mb-1 text-[10px] uppercase tracking-wide text-muted">
                Scenario
              </div>
              <Select value={effective} onChange={(e) => setSelectedId(e.target.value)}>
                {(scenarios ?? []).map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </div>
            {stats && (
              <div className="flex flex-wrap items-end gap-2 text-xs text-muted">
                <Pill label="Mean">{fmt.money(stats.mean)}</Pill>
                <Pill label="Std dev">{fmt.money(stats.std)}</Pill>
                <Pill label="P50">{fmt.money(stats.p50)}</Pill>
                <Pill label="P95">{fmt.money(stats.p95)}</Pill>
                <Pill label="P99">{fmt.money(stats.p99)}</Pill>
              </div>
            )}
            <div className="flex-1" />
            <Button variant="outline" onClick={downloadCsv} disabled={!rows.length}>
              <Download className="h-4 w-4" />
              Export CSV
            </Button>
            <Button variant="outline" onClick={downloadJson} disabled={!rows.length}>
              <Download className="h-4 w-4" />
              Export JSON
            </Button>
          </div>
          {!runId ? (
            <p className="text-sm text-muted">
              No simulation has been run for this scenario yet. Go to the Workspace and click Run.
            </p>
          ) : isLoading ? (
            <p className="text-sm text-muted">Loading iteration data…</p>
          ) : (
            <div className="overflow-auto" style={{ maxHeight: "calc(100vh - 320px)" }}>
              <table className="w-full text-sm">
                <thead>
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((h) => (
                        <th
                          key={h.id}
                          onClick={h.column.getToggleSortingHandler()}
                          className="sticky top-0 z-10 cursor-pointer border-b bg-[var(--c-border-2)] px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted"
                        >
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {h.column.getIsSorted() === "asc"
                            ? " ↑"
                            : h.column.getIsSorted() === "desc"
                              ? " ↓"
                              : ""}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {visibleRows.map((row) => (
                    <tr
                      key={row.id}
                      className="border-b border-[var(--c-border-2)] hover:bg-background"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-3 py-1.5">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {totalIterations > visibleRows.length && (
                    <tr>
                      <td
                        colSpan={columns.length}
                        className="px-3 py-3 text-center text-xs text-muted"
                      >
                        Showing {visibleRows.length.toLocaleString("en-AU")} of{" "}
                        {totalIterations.toLocaleString("en-AU")} iterations. Use Export CSV
                        for the full vector.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function Pill({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-baseline gap-1 rounded-full bg-[var(--c-border-2)] px-2.5 py-1">
      <span className="text-[10px] uppercase tracking-wider text-muted">{label}</span>
      <span className="font-mono text-ink">{children}</span>
    </span>
  );
}
