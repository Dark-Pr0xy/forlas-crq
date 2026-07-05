import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ChevronRight, ChevronDown, Download } from "lucide-react";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useRegister } from "@/lib/queries";
import { fmt } from "@/lib/format";
import type { RegisterRow } from "@/types/api";

export function RegisterPage() {
  const { data, isLoading } = useRegister();
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([{ id: "ale", desc: true }]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const columns = useMemo<ColumnDef<RegisterRow>[]>(
    () => [
      {
        id: "expand",
        header: "",
        size: 24,
        cell: ({ row }) => (
          <button
            type="button"
            onClick={() => toggleExpand(row.original.scenario_id)}
            className="text-muted hover:text-ink"
            aria-label="Expand row"
          >
            {expanded.has(row.original.scenario_id) ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </button>
        ),
      },
      {
        id: "name",
        header: "Scenario",
        accessorKey: "name",
        cell: ({ row }) => (
          <div>
            <div className="font-medium text-ink">{row.original.name}</div>
            <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[11px] text-muted">
              {row.original.business_unit ?? "—"}
              {row.original.owner_label ? ` · ${row.original.owner_label}` : ""}
              {row.original.tags.map((t) => (
                <Badge key={t} tone="neutral">
                  {t}
                </Badge>
              ))}
            </div>
          </div>
        ),
      },
      {
        id: "mode",
        header: "Mode",
        accessorKey: "mode",
        cell: (c) => <Badge tone="accent">{c.getValue<string>()}</Badge>,
      },
      {
        id: "ale",
        header: "ALE",
        accessorFn: (r) => r.ale ?? -1,
        cell: ({ row }) =>
          row.original.ale != null ? (
            <span className="font-mono">{fmt.money(row.original.ale)}</span>
          ) : (
            <span className="text-muted">—</span>
          ),
      },
      {
        id: "p95",
        header: "P95",
        accessorFn: (r) => r.p95 ?? -1,
        cell: ({ row }) =>
          row.original.p95 != null ? (
            <span className="font-mono">{fmt.money(row.original.p95)}</span>
          ) : (
            <span className="text-muted">—</span>
          ),
      },
      {
        id: "p99",
        header: "P99",
        accessorFn: (r) => r.p99 ?? -1,
        cell: ({ row }) =>
          row.original.p99 != null ? (
            <span className="font-mono">{fmt.money(row.original.p99)}</span>
          ) : (
            <span className="text-muted">—</span>
          ),
      },
      {
        id: "tolerance",
        header: "Tolerance",
        accessorKey: "tolerance",
        cell: ({ row }) => (
          <span className="font-mono">{fmt.money(row.original.tolerance)}</span>
        ),
      },
      {
        id: "utilisation",
        header: "Utilisation",
        accessorFn: (r) => r.utilisation ?? -1,
        cell: ({ row }) =>
          row.original.utilisation != null ? (
            <Badge tone={row.original.over_tolerance ? "rose" : "success"}>
              {fmt.pct(row.original.utilisation, 0)}
            </Badge>
          ) : (
            <span className="text-muted">—</span>
          ),
      },
      {
        id: "last_simulated_at",
        header: "Last run",
        accessorFn: (r) => r.last_simulated_at ?? "",
        cell: ({ row }) => (
          <span className="font-mono text-[11.5px] text-muted">
            {fmt.date(row.original.last_simulated_at)}
          </span>
        ),
      },
    ],
    [expanded],
  );

  const table = useReactTable({
    data: data ?? [],
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: (row, _, filterValue) => {
      const q = String(filterValue).toLowerCase();
      const s = row.original;
      return (
        s.name.toLowerCase().includes(q) ||
        (s.business_unit ?? "").toLowerCase().includes(q) ||
        (s.owner_label ?? "").toLowerCase().includes(q) ||
        s.tags.some((t) => t.toLowerCase().includes(q)) ||
        s.mode.toLowerCase().includes(q)
      );
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function downloadCsv() {
    const rows = (data ?? []).map((r) => [
      r.name,
      r.business_unit ?? "",
      r.owner_label ?? "",
      r.mode,
      r.ale ?? "",
      r.p50 ?? "",
      r.p95 ?? "",
      r.p99 ?? "",
      r.tolerance,
      r.utilisation ?? "",
      r.prob_exceed_tolerance ?? "",
      r.over_tolerance,
      r.last_simulated_at ?? "",
      r.version_label,
    ]);
    const lines = [
      "Scenario,Business Unit,Owner,Mode,ALE,P50,P95,P99,Tolerance,Utilisation,P(>Tolerance),Over Tolerance,Last Run,Version",
      ...rows.map((row) =>
        row
          .map((v) => {
            const s = String(v);
            return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
          })
          .join(","),
      ),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "exposure_register.csv";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(url);
      a.remove();
    }, 200);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quantified exposure register</CardTitle>
        <CardHint>
          {data ? `${table.getFilteredRowModel().rows.length} / ${data.length}` : "0 / 0"} rows
        </CardHint>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-[320px]">
            <Input
              placeholder="Filter by name, BU, owner, tag…"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
            />
          </div>
          <div className="flex-1" />
          <Button variant="outline" onClick={downloadCsv} disabled={!data?.length}>
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
        </div>
        {isLoading ? (
          <p className="text-sm text-muted">Loading register…</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((h) => (
                      <th
                        key={h.id}
                        onClick={h.column.getToggleSortingHandler()}
                        className="cursor-pointer border-b bg-[var(--c-border-2)] px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-muted"
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
                {table.getRowModel().rows.map((row) => (
                  <RowWithExpansion
                    key={row.id}
                    row={row}
                    expanded={expanded.has(row.original.scenario_id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function RowWithExpansion({
  row,
  expanded,
}: {
  row: import("@tanstack/react-table").Row<RegisterRow>;
  expanded: boolean;
}) {
  return (
    <>
      <tr className="border-b border-[var(--c-border-2)] hover:bg-background">
        {row.getVisibleCells().map((cell) => (
          <td key={cell.id} className="px-3 py-2 align-middle">
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </td>
        ))}
      </tr>
      {expanded && (
        <tr className="bg-[var(--c-border-2)]/40">
          <td colSpan={row.getVisibleCells().length} className="px-6 py-3 text-xs text-muted">
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 md:grid-cols-4">
              <Field label="Mode" value={row.original.mode} />
              <Field
                label="P(L > Tolerance)"
                value={
                  row.original.prob_exceed_tolerance != null
                    ? fmt.pct(row.original.prob_exceed_tolerance, 2)
                    : "—"
                }
              />
              <Field label="Tail mean" value={fmt.money(row.original.tail_mean ?? 0)} />
              <Field label="Version" value={row.original.version_label} />
              <Field label="Review date" value={row.original.review_date ?? "—"} />
              <Field label="Last simulated" value={fmt.date(row.original.last_simulated_at)} />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className="font-mono text-ink">{value}</div>
    </div>
  );
}
