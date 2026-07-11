import { useEffect, useMemo, useState } from "react";
import { useSearch } from "@tanstack/react-router";
import { Plus, Save, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { apiErrorMessage } from "@/lib/api";
import { fmt } from "@/lib/format";
import { useAnalysis, useSaveAnalysis, useScenarios } from "@/lib/queries";
import { stableStringify } from "@/lib/stableStringify";
import { useAuth } from "@/store/auth";
import type {
  AnalysisRecord,
  Assumption,
  DataSource,
  DecompositionMode,
  Gap,
} from "@/types/api";

const VARIABLE_LABELS: Record<string, string> = {
  lef: "Loss Event Frequency",
  tef: "Threat Event Frequency",
  vuln: "Vulnerability",
  tcap: "Threat Capability",
  rs: "Resistance Strength",
  plm: "Primary Loss Magnitude",
  slp_prob: "Secondary Loss Probability",
  slm: "Secondary Loss Magnitude",
};

function visibleVariables(mode: DecompositionMode): string[] {
  if (mode === "lef") return ["lef", "plm", "slp_prob", "slm"];
  if (mode === "tef-vuln") return ["tef", "vuln", "plm", "slp_prob", "slm"];
  return ["tef", "tcap", "rs", "plm", "slp_prob", "slm"];
}

const LEVELS = ["", "low", "medium", "high"] as const;

type Draft = Pick<
  AnalysisRecord,
  "summary" | "confidence" | "data_sources" | "assumptions" | "gaps" | "input_rationale"
>;

function toDraft(rec: AnalysisRecord | undefined): Draft {
  return {
    summary: rec?.summary ?? "",
    confidence: rec?.confidence ?? "",
    data_sources: rec?.data_sources ?? [],
    assumptions: rec?.assumptions ?? [],
    gaps: rec?.gaps ?? [],
    input_rationale: rec?.input_rationale ?? {},
  };
}

/** Drop rows whose required field is blank so the API doesn't 422. */
function cleaned(draft: Draft): Draft {
  return {
    summary: (draft.summary ?? "").trim() || null,
    confidence: (draft.confidence ?? "").trim() || null,
    data_sources: draft.data_sources.filter((d) => (d.title ?? "").trim()),
    assumptions: draft.assumptions.filter((a) => (a.statement ?? "").trim()),
    gaps: draft.gaps.filter((g) => (g.description ?? "").trim()),
    input_rationale: Object.fromEntries(
      Object.entries(draft.input_rationale).filter(([, v]) => (v ?? "").trim()),
    ),
  };
}

export function AnalysisEvidencePage() {
  const { data: scenarios } = useScenarios();
  const role = useAuth((s) => s.user?.role);
  const canEdit = role !== "readonly";

  // Deep link from the Workspace: /analysis?scenario=<id>.
  const search = useSearch({ strict: false }) as { scenario?: string };
  const [selectedId, setSelectedId] = useState<string | null>(search.scenario ?? null);
  useEffect(() => {
    if (search.scenario) setSelectedId(search.scenario);
  }, [search.scenario]);
  useEffect(() => {
    if (!selectedId && scenarios && scenarios.length > 0) setSelectedId(scenarios[0].id);
  }, [scenarios, selectedId]);

  const selected = useMemo(
    () => scenarios?.find((s) => s.id === selectedId) ?? null,
    [scenarios, selectedId],
  );

  const { data: analysis, isLoading } = useAnalysis(selectedId);
  const save = useSaveAnalysis(selectedId ?? "");

  const [draft, setDraft] = useState<Draft>(toDraft(undefined));
  const [saveError, setSaveError] = useState<string | null>(null);

  // Reset the editable copy whenever we load a different scenario's analysis.
  // Keyed on id + updated_at (not the object) so in-progress edits aren't
  // clobbered by unrelated refetches of an unchanged record.
  useEffect(() => {
    setDraft(toDraft(analysis));
    setSaveError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, analysis?.updated_at]);

  const loadedFingerprint = analysis
    ? stableStringify(cleaned(toDraft(analysis)))
    : stableStringify(cleaned(toDraft(undefined)));
  const isDirty = stableStringify(cleaned(draft)) !== loadedFingerprint;

  function patch(p: Partial<Draft>) {
    setDraft((d) => ({ ...d, ...p }));
  }

  function onSave() {
    if (!selectedId) return;
    save.mutate(cleaned(draft), {
      onSuccess: () => setSaveError(null),
      onError: (e) => setSaveError(apiErrorMessage(e)),
    });
  }

  if (!scenarios) {
    return <p className="text-sm text-muted">Loading scenarios…</p>;
  }

  const variables = selected ? visibleVariables(selected.mode) : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Analysis &amp; Evidence</h2>
          <p className="text-xs text-muted">
            Capture the reasoning behind the numbers — the data relied on, the assumptions made,
            and the gaps a reviewer should know about.
          </p>
        </div>
        <div className="flex items-end gap-2">
          <div className="w-64">
            <Label className="text-[11px]">Scenario</Label>
            <Select
              value={selectedId ?? ""}
              onChange={(e) => setSelectedId(e.target.value || null)}
            >
              {scenarios.length === 0 && <option value="">No scenarios</option>}
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </div>
          {isDirty && (
            <Badge tone="amber" className="mb-1.5">
              Unsaved
            </Badge>
          )}
          <Button
            onClick={onSave}
            disabled={!canEdit || !isDirty || save.isPending || !selectedId}
            title={canEdit ? undefined : "Read-only role cannot edit analysis"}
          >
            <Save className="h-4 w-4" />
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>

      {!selectedId ? (
        <Card>
          <CardBody>
            <p className="text-muted">
              {scenarios.length === 0
                ? "No scenarios yet — create one in the Workspace to attach analysis."
                : "Pick a scenario above to record its analysis and evidence."}
            </p>
          </CardBody>
        </Card>
      ) : isLoading ? (
        <p className="text-sm text-muted">Loading analysis…</p>
      ) : (
        <>
          {saveError && (
            <div className="rounded border border-rose px-3 py-2 text-xs text-rose">
              <span className="font-semibold">Save failed:</span> {saveError}
            </div>
          )}
          {!canEdit && (
            <div className="rounded border border-amber bg-amber-soft px-3 py-2 text-xs text-amber">
              Your role is read-only — you can view this analysis but not change it.
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
            <div className="space-y-4">
              {/* Analysis summary */}
              <Card>
                <CardHeader>
                  <CardTitle>Analysis summary</CardTitle>
                  {analysis?.updated_at && (
                    <CardHint>Last updated {fmt.date(analysis.updated_at)}</CardHint>
                  )}
                </CardHeader>
                <CardBody className="space-y-3">
                  <div className="space-y-1">
                    <Label>Narrative</Label>
                    <Textarea
                      rows={6}
                      placeholder="How was this scenario scoped and estimated? What is the loss story, and what drives it?"
                      value={draft.summary ?? ""}
                      disabled={!canEdit}
                      onChange={(e) => patch({ summary: e.target.value })}
                    />
                  </div>
                  <div className="w-48 space-y-1">
                    <Label>Overall confidence</Label>
                    <Select
                      value={draft.confidence ?? ""}
                      disabled={!canEdit}
                      onChange={(e) => patch({ confidence: e.target.value })}
                    >
                      <option value="">Not stated</option>
                      {LEVELS.filter(Boolean).map((l) => (
                        <option key={l} value={l}>
                          {l}
                        </option>
                      ))}
                    </Select>
                  </div>
                </CardBody>
              </Card>

              {/* Data relied upon */}
              <ListCard
                title="Data relied upon"
                hint="Sources, evidence and references used in the estimate"
                count={draft.data_sources.length}
                canEdit={canEdit}
                onAdd={() =>
                  patch({
                    data_sources: [
                      ...draft.data_sources,
                      { title: "", description: "", reference: "", date: "", confidence: "" },
                    ],
                  })
                }
                emptyText="No data sources recorded yet."
              >
                {draft.data_sources.map((row, i) => (
                  <RowShell
                    key={i}
                    canEdit={canEdit}
                    onRemove={() =>
                      patch({ data_sources: draft.data_sources.filter((_, j) => j !== i) })
                    }
                  >
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <LabeledInput
                        label="Title / source"
                        value={row.title}
                        disabled={!canEdit}
                        onChange={(v) => updateItem(draft, patch, "data_sources", i, { title: v })}
                      />
                      <LabeledInput
                        label="Reference (URL or citation)"
                        value={row.reference ?? ""}
                        disabled={!canEdit}
                        onChange={(v) =>
                          updateItem(draft, patch, "data_sources", i, { reference: v })
                        }
                      />
                      <LabeledInput
                        label="Date"
                        type="date"
                        value={row.date ?? ""}
                        disabled={!canEdit}
                        onChange={(v) => updateItem(draft, patch, "data_sources", i, { date: v })}
                      />
                      <LabeledLevel
                        label="Confidence in source"
                        value={row.confidence ?? ""}
                        disabled={!canEdit}
                        onChange={(v) =>
                          updateItem(draft, patch, "data_sources", i, { confidence: v })
                        }
                      />
                    </div>
                    <div className="mt-2 space-y-1">
                      <Label>What it tells us</Label>
                      <Textarea
                        rows={2}
                        value={row.description ?? ""}
                        disabled={!canEdit}
                        onChange={(e) =>
                          updateItem(draft, patch, "data_sources", i, {
                            description: e.target.value,
                          })
                        }
                      />
                    </div>
                  </RowShell>
                ))}
              </ListCard>

              {/* Assumptions */}
              <ListCard
                title="Assumptions"
                hint="Judgements made where data was thin"
                count={draft.assumptions.length}
                canEdit={canEdit}
                onAdd={() =>
                  patch({
                    assumptions: [
                      ...draft.assumptions,
                      { statement: "", rationale: "", impact: "" },
                    ],
                  })
                }
                emptyText="No assumptions recorded yet."
              >
                {draft.assumptions.map((row, i) => (
                  <RowShell
                    key={i}
                    canEdit={canEdit}
                    onRemove={() =>
                      patch({ assumptions: draft.assumptions.filter((_, j) => j !== i) })
                    }
                  >
                    <div className="space-y-2">
                      <LabeledInput
                        label="Assumption"
                        value={row.statement}
                        disabled={!canEdit}
                        onChange={(v) =>
                          updateItem(draft, patch, "assumptions", i, { statement: v })
                        }
                      />
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <LabeledInput
                          label="Rationale"
                          value={row.rationale ?? ""}
                          disabled={!canEdit}
                          onChange={(v) =>
                            updateItem(draft, patch, "assumptions", i, { rationale: v })
                          }
                        />
                        <LabeledInput
                          label="Impact if wrong"
                          value={row.impact ?? ""}
                          disabled={!canEdit}
                          onChange={(v) =>
                            updateItem(draft, patch, "assumptions", i, { impact: v })
                          }
                        />
                      </div>
                    </div>
                  </RowShell>
                ))}
              </ListCard>

              {/* Gaps & limitations */}
              <ListCard
                title="Gaps & limitations"
                hint="What we don't know, and how it could bias the result"
                count={draft.gaps.length}
                canEdit={canEdit}
                onAdd={() =>
                  patch({
                    gaps: [...draft.gaps, { description: "", severity: "", mitigation: "" }],
                  })
                }
                emptyText="No gaps recorded yet."
              >
                {draft.gaps.map((row, i) => (
                  <RowShell
                    key={i}
                    canEdit={canEdit}
                    onRemove={() => patch({ gaps: draft.gaps.filter((_, j) => j !== i) })}
                  >
                    <div className="space-y-2">
                      <LabeledInput
                        label="Gap / limitation"
                        value={row.description}
                        disabled={!canEdit}
                        onChange={(v) => updateItem(draft, patch, "gaps", i, { description: v })}
                      />
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <LabeledLevel
                          label="Severity"
                          value={row.severity ?? ""}
                          disabled={!canEdit}
                          onChange={(v) => updateItem(draft, patch, "gaps", i, { severity: v })}
                        />
                        <LabeledInput
                          label="Mitigation / plan"
                          value={row.mitigation ?? ""}
                          disabled={!canEdit}
                          onChange={(v) => updateItem(draft, patch, "gaps", i, { mitigation: v })}
                        />
                      </div>
                    </div>
                  </RowShell>
                ))}
              </ListCard>
            </div>

            {/* Per-input rationale */}
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Input rationale</CardTitle>
                  <CardHint>Why each estimate</CardHint>
                </CardHeader>
                <CardBody className="space-y-3">
                  <p className="text-xs text-muted">
                    A short justification for each FAIR input in{" "}
                    <span className="font-medium">{selected?.name}</span>.
                  </p>
                  {variables.map((key) => (
                    <div key={key} className="space-y-1">
                      <Label>{VARIABLE_LABELS[key] ?? key}</Label>
                      <Textarea
                        rows={2}
                        placeholder="Basis for this estimate…"
                        value={draft.input_rationale[key] ?? ""}
                        disabled={!canEdit}
                        onChange={(e) =>
                          patch({
                            input_rationale: {
                              ...draft.input_rationale,
                              [key]: e.target.value,
                            },
                          })
                        }
                      />
                    </div>
                  ))}
                </CardBody>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ helpers

type ListKey = "data_sources" | "assumptions" | "gaps";

function updateItem(
  draft: Draft,
  patch: (p: Partial<Draft>) => void,
  key: ListKey,
  index: number,
  changes: Partial<DataSource & Assumption & Gap>,
) {
  const next = draft[key].map((item, j) =>
    j === index ? { ...item, ...changes } : item,
  );
  patch({ [key]: next } as Partial<Draft>);
}

function ListCard({
  title,
  hint,
  count,
  canEdit,
  onAdd,
  emptyText,
  children,
}: {
  title: React.ReactNode;
  hint: string;
  count: number;
  canEdit: boolean;
  onAdd: () => void;
  emptyText: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardHint>{hint}</CardHint>
      </CardHeader>
      <CardBody className="space-y-3">
        {count === 0 ? (
          <p className="text-xs text-muted">{emptyText}</p>
        ) : (
          <div className="space-y-3">{children}</div>
        )}
        <Button size="sm" variant="outline" onClick={onAdd} disabled={!canEdit}>
          <Plus className="h-4 w-4" />
          Add
        </Button>
      </CardBody>
    </Card>
  );
}

function RowShell({
  canEdit,
  onRemove,
  children,
}: {
  canEdit: boolean;
  onRemove: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded border border-[var(--c-border-2)] p-3">
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">{children}</div>
        <button
          type="button"
          onClick={onRemove}
          disabled={!canEdit}
          className="rounded p-1 text-muted hover:text-rose disabled:opacity-40"
          title="Remove"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function LabeledInput({
  label,
  value,
  onChange,
  disabled,
  type,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input
        type={type}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function LabeledLevel({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Select value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        <option value="">Not stated</option>
        {LEVELS.filter(Boolean).map((l) => (
          <option key={l} value={l}>
            {l}
          </option>
        ))}
      </Select>
    </div>
  );
}
