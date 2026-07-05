import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";

interface ThreatEntry {
  id: string;
  name: string;
  category: string | null;
  source: string;
  description: string | null;
  references: string[];
  attributes: Record<string, unknown> | null;
}

interface ControlEntry {
  id: string;
  framework: string;
  code: string;
  name: string;
  description: string | null;
  category: string | null;
  source: string;
}

interface BenchmarkEntry {
  id: string;
  name: string;
  industry: string | null;
  metric: string;
  distribution: Record<string, unknown>;
  citation: string | null;
  source: string;
}

export function KnowledgePage() {
  const [tab, setTab] = useState("threats");
  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList>
        <TabsTrigger value="threats">Threats</TabsTrigger>
        <TabsTrigger value="controls">Controls</TabsTrigger>
        <TabsTrigger value="benchmarks">Benchmarks</TabsTrigger>
      </TabsList>
      <TabsContent value="threats">
        <ThreatsTab />
      </TabsContent>
      <TabsContent value="controls">
        <ControlsTab />
      </TabsContent>
      <TabsContent value="benchmarks">
        <BenchmarksTab />
      </TabsContent>
    </Tabs>
  );
}

// ============================================================================
// Threats
// ============================================================================

interface ThreatForm {
  name: string;
  category: string;
  description: string;
  references: string;
}

function ThreatsTab() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<ThreatEntry | "new" | null>(null);
  const { data, isLoading } = useQuery<ThreatEntry[]>({
    queryKey: ["knowledge", "threats"],
    queryFn: () => api.get<ThreatEntry[]>("/api/knowledge/threats"),
  });
  const saveMut = useMutation({
    mutationFn: async (vars: { id?: string; payload: ThreatForm }) => {
      const body = {
        name: vars.payload.name.trim(),
        category: vars.payload.category.trim() || null,
        description: vars.payload.description.trim() || null,
        references: vars.payload.references
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      if (vars.id) {
        return api.patch<ThreatEntry>(`/api/knowledge/threats/${vars.id}`, body);
      }
      return api.post<ThreatEntry>("/api/knowledge/threats", body);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", "threats"] }),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/knowledge/threats/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", "threats"] }),
  });

  const filtered = useMemo(() => {
    if (!data) return [];
    const term = q.trim().toLowerCase();
    if (!term) return data;
    return data.filter(
      (t) =>
        t.name.toLowerCase().includes(term) ||
        (t.category ?? "").toLowerCase().includes(term) ||
        (t.description ?? "").toLowerCase().includes(term),
    );
  }, [data, q]);

  const grouped = useMemo(() => {
    const out: Record<string, ThreatEntry[]> = {};
    for (const t of filtered) {
      const k = t.category ?? "Uncategorised";
      (out[k] ??= []).push(t);
    }
    return out;
  }, [filtered]);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Threat library</CardTitle>
          <CardHint>
            FAIR threat communities · MITRE ATT&amp;CK starter set · custom entries
          </CardHint>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Search threats…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="max-w-[360px]"
            />
            <div className="flex-1" />
            <Button onClick={() => setEditing("new")}>
              <Plus className="h-4 w-4" />
              Add threat
            </Button>
          </div>
          {isLoading ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : (
            <div className="space-y-5">
              {Object.entries(grouped).map(([cat, items]) => (
                <div key={cat}>
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                    {cat}
                  </h3>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    {items.map((t) => (
                      <div
                        key={t.id}
                        className="group relative rounded border bg-surface p-3 transition hover:border-accent/50"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="font-medium text-ink">{t.name}</div>
                          <Badge tone={t.source === "builtin" ? "neutral" : "accent"}>
                            {t.source}
                          </Badge>
                        </div>
                        {t.description && (
                          <p className="mt-1.5 text-[12.5px] leading-snug text-muted">
                            {t.description}
                          </p>
                        )}
                        {t.references && t.references.length > 0 && (
                          <div className="mt-2 text-[11px] text-muted">
                            {t.references.map((r) => (
                              <div key={r} className="font-mono">
                                ↗ {r}
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="mt-2 flex justify-end gap-1 opacity-0 transition group-hover:opacity-100">
                          <Button
                            size="icon"
                            variant="ghost"
                            title="Edit"
                            onClick={() => setEditing(t)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            title={
                              t.source === "builtin"
                                ? "Delete (will be restored on next restart)"
                                : "Delete"
                            }
                            onClick={() => {
                              const note =
                                t.source === "builtin"
                                  ? `\n\nThis is a built-in entry — it will be re-seeded on the next backend restart.`
                                  : "";
                              if (confirm(`Delete threat "${t.name}"?${note}`))
                                deleteMut.mutate(t.id);
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {filtered.length === 0 && (
                <p className="text-sm text-muted">No threats match.</p>
              )}
            </div>
          )}
        </CardBody>
      </Card>
      {editing && (
        <ThreatDialog
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSave={async (form) => {
            await saveMut.mutateAsync({
              id: editing === "new" ? undefined : editing.id,
              payload: form,
            });
            setEditing(null);
          }}
        />
      )}
    </>
  );
}

function ThreatDialog({
  initial,
  onClose,
  onSave,
}: {
  initial: ThreatEntry | null;
  onClose: () => void;
  onSave: (form: ThreatForm) => Promise<void>;
}) {
  const [form, setForm] = useState<ThreatForm>({
    name: initial?.name ?? "",
    category: initial?.category ?? "",
    description: initial?.description ?? "",
    references: (initial?.references ?? []).join("\n"),
  });
  const [saving, setSaving] = useState(false);

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit threat" : "New threat"}</DialogTitle>
          <DialogDescription>
            Custom entries live alongside built-ins and can be filtered, edited and deleted.
          </DialogDescription>
        </DialogHeader>
        <div className="mt-3 space-y-3">
          <Field label="Name">
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              autoFocus
            />
          </Field>
          <Field label="Category">
            <Input
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            />
          </Field>
          <Field label="Description">
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </Field>
          <Field label="References (one per line)">
            <Textarea
              value={form.references}
              onChange={(e) => setForm({ ...form, references: e.target.value })}
            />
          </Field>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!form.name.trim() || saving}
            onClick={async () => {
              setSaving(true);
              try {
                await onSave(form);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Controls
// ============================================================================

interface ControlForm {
  framework: string;
  code: string;
  name: string;
  description: string;
  category: string;
}

function ControlsTab() {
  const qc = useQueryClient();
  const [framework, setFramework] = useState<string>("");
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<ControlEntry | "new" | null>(null);

  const { data: all } = useQuery<ControlEntry[]>({
    queryKey: ["knowledge", "controls"],
    queryFn: () => api.get<ControlEntry[]>("/api/knowledge/controls"),
  });
  const frameworks = useMemo(() => {
    const set = new Set<string>();
    (all ?? []).forEach((c) => set.add(c.framework));
    return Array.from(set).sort();
  }, [all]);
  const rows = useMemo(() => {
    if (!all) return [];
    const term = q.trim().toLowerCase();
    return all.filter(
      (c) =>
        (!framework || c.framework === framework) &&
        (!term ||
          c.name.toLowerCase().includes(term) ||
          c.code.toLowerCase().includes(term)),
    );
  }, [all, framework, q]);

  const saveMut = useMutation({
    mutationFn: async (vars: { id?: string; payload: ControlForm }) => {
      const body = {
        framework: vars.payload.framework.trim(),
        code: vars.payload.code.trim(),
        name: vars.payload.name.trim(),
        description: vars.payload.description.trim() || null,
        category: vars.payload.category.trim() || null,
      };
      if (vars.id)
        return api.patch<ControlEntry>(`/api/knowledge/controls/${vars.id}`, body);
      return api.post<ControlEntry>("/api/knowledge/controls", body);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", "controls"] }),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/knowledge/controls/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", "controls"] }),
  });

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Control catalogue</CardTitle>
          <CardHint>{rows.length} controls visible</CardHint>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <Input
              placeholder="Search controls…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="max-w-[280px]"
            />
            <div className="w-[240px]">
              <Select value={framework} onChange={(e) => setFramework(e.target.value)}>
                <option value="">All frameworks</option>
                {frameworks.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex-1" />
            <Button onClick={() => setEditing("new")}>
              <Plus className="h-4 w-4" />
              Add control
            </Button>
          </div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted">
                  <th className="py-2 pr-2">Framework</th>
                  <th className="py-2 pr-2">Code</th>
                  <th className="py-2 pr-2">Name</th>
                  <th className="py-2 pr-2">Category</th>
                  <th className="py-2 pr-2"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr
                    key={c.id}
                    className="group border-b border-[var(--c-border-2)] hover:bg-background"
                  >
                    <td className="py-1.5 pr-2 text-muted">{c.framework}</td>
                    <td className="py-1.5 pr-2 font-mono text-[11.5px]">{c.code}</td>
                    <td className="py-1.5 pr-2">{c.name}</td>
                    <td className="py-1.5 pr-2 text-muted">{c.category ?? "—"}</td>
                    <td className="py-1.5 pr-2 text-right">
                      <div className="flex justify-end gap-1 opacity-0 transition group-hover:opacity-100">
                        <Button
                          size="icon"
                          variant="ghost"
                          title="Edit"
                          onClick={() => setEditing(c)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          title={
                            c.source === "builtin"
                              ? "Delete (will be restored on next restart)"
                              : "Delete"
                          }
                          onClick={() => {
                            const note =
                              c.source === "builtin"
                                ? "\n\nThis is a built-in entry — it will be re-seeded on the next backend restart."
                                : "";
                            if (confirm(`Delete control ${c.code}?${note}`))
                              deleteMut.mutate(c.id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
      {editing && (
        <ControlDialog
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSave={async (form) => {
            await saveMut.mutateAsync({
              id: editing === "new" ? undefined : editing.id,
              payload: form,
            });
            setEditing(null);
          }}
        />
      )}
    </>
  );
}

function ControlDialog({
  initial,
  onClose,
  onSave,
}: {
  initial: ControlEntry | null;
  onClose: () => void;
  onSave: (form: ControlForm) => Promise<void>;
}) {
  const [form, setForm] = useState<ControlForm>({
    framework: initial?.framework ?? "",
    code: initial?.code ?? "",
    name: initial?.name ?? "",
    description: initial?.description ?? "",
    category: initial?.category ?? "",
  });
  const [saving, setSaving] = useState(false);

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit control" : "New control"}</DialogTitle>
        </DialogHeader>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Field label="Framework">
            <Input
              value={form.framework}
              onChange={(e) => setForm({ ...form, framework: e.target.value })}
              autoFocus
            />
          </Field>
          <Field label="Code">
            <Input
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
            />
          </Field>
          <div className="col-span-2">
            <Field label="Name">
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </Field>
          </div>
          <Field label="Category">
            <Input
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            />
          </Field>
          <div className="col-span-2">
            <Field label="Description">
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </Field>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={
              !form.framework.trim() ||
              !form.code.trim() ||
              !form.name.trim() ||
              saving
            }
            onClick={async () => {
              setSaving(true);
              try {
                await onSave(form);
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Benchmarks
// ============================================================================

interface BenchmarkForm {
  name: string;
  industry: string;
  metric: string;
  distributionJson: string;
  citation: string;
}

function BenchmarksTab() {
  const qc = useQueryClient();
  const [industry, setIndustry] = useState("");
  const [metric, setMetric] = useState("");
  const [editing, setEditing] = useState<BenchmarkEntry | "new" | null>(null);

  // Fetch the full catalogue once and filter client-side (M2). Deriving the
  // dropdown options from a pre-filtered response made every other option
  // vanish the moment you picked one.
  const { data: all } = useQuery<BenchmarkEntry[]>({
    queryKey: ["knowledge", "benchmarks"],
    queryFn: () => api.get<BenchmarkEntry[]>("/api/knowledge/benchmarks"),
  });
  const industries = useMemo(() => {
    const set = new Set<string>();
    (all ?? []).forEach((b) => b.industry && set.add(b.industry));
    return Array.from(set).sort();
  }, [all]);
  const metrics = useMemo(() => {
    const set = new Set<string>();
    (all ?? []).forEach((b) => set.add(b.metric));
    return Array.from(set).sort();
  }, [all]);
  const data = useMemo(() => {
    return (all ?? []).filter(
      (b) =>
        (!industry || b.industry === industry) && (!metric || b.metric === metric),
    );
  }, [all, industry, metric]);

  const saveMut = useMutation({
    mutationFn: async (vars: { id?: string; payload: BenchmarkForm }) => {
      let distribution: Record<string, unknown>;
      try {
        distribution = JSON.parse(vars.payload.distributionJson);
      } catch {
        throw new Error("Distribution must be valid JSON");
      }
      const body = {
        name: vars.payload.name.trim(),
        industry: vars.payload.industry.trim() || null,
        metric: vars.payload.metric.trim(),
        distribution,
        citation: vars.payload.citation.trim() || null,
      };
      if (vars.id)
        return api.patch<BenchmarkEntry>(`/api/knowledge/benchmarks/${vars.id}`, body);
      return api.post<BenchmarkEntry>("/api/knowledge/benchmarks", body);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", "benchmarks"] }),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => api.delete(`/api/knowledge/benchmarks/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["knowledge", "benchmarks"] }),
  });

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Reference benchmarks</CardTitle>
          <CardHint>Frequency &amp; magnitude starting points by industry</CardHint>
        </CardHeader>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-[200px]">
              <Select value={industry} onChange={(e) => setIndustry(e.target.value)}>
                <option value="">All industries</option>
                {industries.map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-[200px]">
              <Select value={metric} onChange={(e) => setMetric(e.target.value)}>
                <option value="">All metrics</option>
                {metrics.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex-1" />
            <Button onClick={() => setEditing("new")}>
              <Plus className="h-4 w-4" />
              Add benchmark
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {(data ?? []).map((b) => (
              <div key={b.id} className="group relative rounded border bg-surface p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="font-medium text-ink">{b.name}</div>
                  <Badge tone="accent">{b.metric}</Badge>
                </div>
                <p className="mt-1 text-[11px] text-muted">
                  Industry: {b.industry ?? "—"} · source: {b.source}
                </p>
                <pre className="mt-2 overflow-auto rounded bg-[var(--c-border-2)] p-2 font-mono text-[11px]">
                  {JSON.stringify(b.distribution, null, 2)}
                </pre>
                {b.citation && (
                  <p className="mt-1 text-[11px] italic text-muted">{b.citation}</p>
                )}
                <div className="mt-2 flex justify-end gap-1 opacity-0 transition group-hover:opacity-100">
                  <Button
                    size="icon"
                    variant="ghost"
                    title="Edit"
                    onClick={() => setEditing(b)}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    size="icon"
                    variant="ghost"
                    title={
                      b.source === "builtin"
                        ? "Delete (will be restored on next restart)"
                        : "Delete"
                    }
                    onClick={() => {
                      const note =
                        b.source === "builtin"
                          ? "\n\nThis is a built-in entry — it will be re-seeded on the next backend restart."
                          : "";
                      if (confirm(`Delete benchmark "${b.name}"?${note}`))
                        deleteMut.mutate(b.id);
                    }}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
          {(data?.length ?? 0) === 0 && (
            <p className="text-sm text-muted">No benchmarks match your filters.</p>
          )}
        </CardBody>
      </Card>
      {editing && (
        <BenchmarkDialog
          initial={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSave={async (form) => {
            await saveMut.mutateAsync({
              id: editing === "new" ? undefined : editing.id,
              payload: form,
            });
            setEditing(null);
          }}
        />
      )}
    </>
  );
}

function BenchmarkDialog({
  initial,
  onClose,
  onSave,
}: {
  initial: BenchmarkEntry | null;
  onClose: () => void;
  onSave: (form: BenchmarkForm) => Promise<void>;
}) {
  const [form, setForm] = useState<BenchmarkForm>({
    name: initial?.name ?? "",
    industry: initial?.industry ?? "",
    metric: initial?.metric ?? "",
    distributionJson: JSON.stringify(
      initial?.distribution ?? { type: "pert", min: 0, mode: 1, max: 5 },
      null,
      2,
    ),
    citation: initial?.citation ?? "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit benchmark" : "New benchmark"}</DialogTitle>
          <DialogDescription>
            Reference distribution that can be copied into a scenario&apos;s inputs.
          </DialogDescription>
        </DialogHeader>
        <div className="mt-3 space-y-3">
          <Field label="Name">
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              autoFocus
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Industry">
              <Input
                value={form.industry}
                onChange={(e) => setForm({ ...form, industry: e.target.value })}
              />
            </Field>
            <Field label="Metric (tef · plm · …)">
              <Input
                value={form.metric}
                onChange={(e) => setForm({ ...form, metric: e.target.value })}
              />
            </Field>
          </div>
          <Field label="Distribution (JSON)">
            <Textarea
              className="font-mono text-xs"
              value={form.distributionJson}
              onChange={(e) =>
                setForm({ ...form, distributionJson: e.target.value })
              }
              rows={6}
            />
          </Field>
          <Field label="Citation">
            <Input
              value={form.citation}
              onChange={(e) => setForm({ ...form, citation: e.target.value })}
            />
          </Field>
          {error && <p className="text-xs text-rose">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            disabled={!form.name.trim() || !form.metric.trim() || saving}
            onClick={async () => {
              setError(null);
              setSaving(true);
              try {
                await onSave(form);
              } catch (e) {
                setError(e instanceof Error ? e.message : "Save failed");
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================================
// Shared
// ============================================================================

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
