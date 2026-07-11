import { useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { FileSearch } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { DistributionParamCard } from "@/components/workspace/DistributionParamCard";
import { ApprovalPanel } from "@/components/workspace/ApprovalPanel";
import { MetadataPanel, type MetadataPanelChanges } from "@/components/workspace/MetadataPanel";
import { ModeSelector } from "@/components/workspace/ModeSelector";
import { NewScenarioDialog } from "@/components/workspace/NewScenarioDialog";
import { RunControls } from "@/components/workspace/RunControls";
import { ScenarioList } from "@/components/workspace/ScenarioList";
import { SimulationResults } from "@/components/workspace/SimulationResults";
import { SortableCards } from "@/components/common/SortableCards";
import { useCardOrder } from "@/lib/useCardOrder";
import {
  useLatestSimulation,
  useScenarios,
  useUpdateScenario,
} from "@/lib/queries";
import { apiErrorMessage } from "@/lib/api";
import { validateScenarioDraft } from "@/lib/validateScenario";
import { stableStringify } from "@/lib/stableStringify";
import type {
  AppSettings,
  DecompositionMode,
  DistributionParam,
  ScenarioInputs,
  ScenarioRead,
} from "@/types/api";

const VARIABLE_DEFS: Record<
  string,
  { title: string; unit?: string; hint?: string }
> = {
  lef: { title: "Loss Event Frequency", unit: "events/yr" },
  tef: { title: "Threat Event Frequency", unit: "events/yr" },
  vuln: { title: "Vulnerability", unit: "probability" },
  tcap: { title: "Threat Capability", unit: "0–100" },
  rs: { title: "Resistance Strength", unit: "0–100" },
  plm: { title: "Primary Loss Magnitude", unit: "AUD / event" },
  slp_prob: { title: "Secondary Loss Probability", unit: "probability" },
  slm: { title: "Secondary Loss Magnitude", unit: "AUD / event" },
};

// Fields the workspace can edit — the only ones that count toward "unsaved".
const _EDITABLE_KEYS = [
  "name",
  "description",
  "business_unit",
  "scenario_type",
  "tags",
  "owner_label",
  "mode",
  "inputs",
  "tolerance",
  "reduction_pct",
  "reference_lines",
  "prefs",
  "version_label",
  "assessment_date",
  "review_date",
  "notes",
  "threat_refs",
  "control_refs",
] as const;

function scenarioFingerprint(s: ScenarioRead): string {
  const projection: Record<string, unknown> = {};
  for (const key of _EDITABLE_KEYS) {
    projection[key] = (s as unknown as Record<string, unknown>)[key] ?? null;
  }
  return stableStringify(projection);
}

function visibleVariables(mode: DecompositionMode): string[] {
  if (mode === "lef") return ["lef", "plm", "slp_prob", "slm"];
  if (mode === "tef-vuln") return ["tef", "vuln", "plm", "slp_prob", "slm"];
  return ["tef", "tcap", "rs", "plm", "slp_prob", "slm"];
}

const WORKSPACE_PANEL_ORDER = ["run", "approval", "metadata"];

export function WorkspacePage() {
  const { data: scenarios } = useScenarios();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draft, setDraft] = useState<ScenarioRead | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId && scenarios && scenarios.length > 0) {
      setSelectedId(scenarios[0].id);
    }
  }, [scenarios, selectedId]);

  const selected = useMemo(
    () => scenarios?.find((s) => s.id === selectedId) ?? null,
    [scenarios, selectedId],
  );

  // Re-baseline the draft only when a different scenario (or a newer server
  // copy) arrives; depending on `selected` itself would clobber typing on
  // every list refetch.
  useEffect(() => {
    if (selected) setDraft(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.id, selected?.updated_at]);

  const { data: settings } = useQuery<AppSettings>({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/api/settings"),
  });
  const { data: latestSim, isLoading: simLoading, error: simError } = useLatestSimulation(
    selectedId,
  );
  const updateMutation = useUpdateScenario(selectedId ?? "");
  const panelOrder = useCardOrder("forlas.workspace_panels", WORKSPACE_PANEL_ORDER);

  // Compare only the editable projection with a key-stable serialisation so
  // server-side key reordering / float round-trips don't fire false "unsaved"
  // states (M9).
  const isDirty = !!(
    draft && selected && scenarioFingerprint(draft) !== scenarioFingerprint(selected)
  );

  // Pre-flight validation — tells the user what's wrong/missing before a
  // save or run round-trips and fails silently.
  const problems = useMemo(
    () =>
      draft
        ? validateScenarioDraft({
            mode: draft.mode,
            inputs: draft.inputs,
            referenceLines: draft.reference_lines,
            approvalState: draft.approval_state,
            isDirty,
          })
        : [],
    [draft, isDirty],
  );

  async function persist(patch: Partial<ScenarioRead>, snapshotNote?: string) {
    if (!selectedId) return;
    try {
      await updateMutation.mutateAsync({ ...patch, snapshot_note: snapshotNote });
      setSaveError(null);
    } catch (e) {
      // Surface the real reason (validation, lock, permission) and rethrow so
      // a save-before-run also halts and reports.
      setSaveError(apiErrorMessage(e));
      throw e;
    }
  }

  function updateDraft(patch: Partial<ScenarioRead>) {
    setDraft((d) => (d ? { ...d, ...patch } : d));
  }

  function updateInput(key: keyof ScenarioInputs, value: DistributionParam) {
    if (!draft) return;
    setDraft({ ...draft, inputs: { ...draft.inputs, [key]: value } });
  }

  function onMetadataChange(patch: MetadataPanelChanges) {
    if (!draft) return;
    setDraft({ ...draft, ...patch });
  }

  if (!scenarios) {
    return <p className="text-sm text-muted">Loading scenarios…</p>;
  }

  return (
    <div
      className="grid grid-cols-[260px_1fr_320px] gap-4"
      style={{ height: "calc(100vh - 54px - 48px)" }}
    >
      <Card className="flex min-h-0 flex-col p-3">
        <ScenarioList
          selectedId={selectedId}
          onSelect={setSelectedId}
          onCreateNew={() => setDialogOpen(true)}
        />
      </Card>

      <div className="flex min-h-0 min-w-0 flex-col gap-4 overflow-y-auto pr-1">
        {!draft ? (
          <Card>
            <CardBody>
              <p className="text-muted">
                {scenarios.length === 0
                  ? "No scenarios yet — create one to get started."
                  : "Pick a scenario on the left."}
              </p>
            </CardBody>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {draft.name}
                  {isDirty && (
                    <span className="rounded-full bg-amber-soft px-2 py-0.5 text-[10px] text-amber">
                      Unsaved
                    </span>
                  )}
                </CardTitle>
                <div className="ml-auto flex items-center gap-2">
                  <Link
                    to="/analysis"
                    search={{ scenario: draft.id }}
                    className="flex items-center gap-1.5 rounded-sm border px-3 py-1 text-xs font-medium text-ink hover:bg-[var(--c-border-2)]"
                    title="Open this scenario's analysis and evidence"
                  >
                    <FileSearch className="h-3.5 w-3.5" />
                    Analysis &amp; evidence
                  </Link>
                  <button
                    type="button"
                    disabled={!isDirty || updateMutation.isPending}
                    className="rounded-sm border bg-accent px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
                    onClick={() => {
                      if (!draft) return;
                      persist(draft).catch(() => {
                        /* reason captured in saveError state */
                      });
                    }}
                  >
                    {updateMutation.isPending ? "Saving…" : "Save"}
                  </button>
                </div>
              </CardHeader>
              <CardBody>
                {(saveError || problems.length > 0) && (
                  <div className="mb-3 space-y-2">
                    {saveError && (
                      <div className="rounded border border-rose px-3 py-2 text-xs text-rose">
                        <span className="font-semibold">Save failed:</span> {saveError}
                      </div>
                    )}
                    {problems.length > 0 && (
                      <div className="rounded border border-amber bg-amber-soft px-3 py-2 text-xs text-amber">
                        <div className="font-semibold">
                          Fix {problems.length} issue{problems.length === 1 ? "" : "s"} before
                          saving or running:
                        </div>
                        <ul className="mt-1 list-disc space-y-0.5 pl-4">
                          {problems.map((p, i) => (
                            <li key={i}>{p}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <ModeSelector
                    value={draft.mode}
                    onChange={(mode) => updateDraft({ mode })}
                  />
                  <div className="grid gap-2">
                    {visibleVariables(draft.mode).map((key) => {
                      const def = VARIABLE_DEFS[key];
                      return (
                        <DistributionParamCard
                          key={key}
                          title={def.title}
                          unit={def.unit}
                          hint={def.hint}
                          value={draft.inputs[key as keyof ScenarioInputs]}
                          onChange={(next) =>
                            updateInput(key as keyof ScenarioInputs, next)
                          }
                        />
                      );
                    })}
                  </div>
                </div>
              </CardBody>
            </Card>

            <SimulationResults
              scenario={draft}
              simulation={latestSim}
              isLoading={simLoading}
              error={simError}
              onScenarioChange={updateDraft}
            />
          </>
        )}
      </div>

      <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
        {draft && settings && (
          <>
            {panelOrder.isCustomized && (
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={panelOrder.reset}
                  className="text-[11px] text-muted hover:text-ink"
                >
                  Reset panel order
                </button>
              </div>
            )}
            <SortableCards
              layout="stack"
              order={panelOrder.order}
              onReorder={panelOrder.apply}
              cards={{
                run: {
                  node: (
                    <RunControls
                      scenario={draft}
                      settings={settings}
                      onReductionChange={(pct) => updateDraft({ reduction_pct: pct })}
                      isDirty={isDirty}
                      problems={problems}
                      onSaveBeforeRun={async () => {
                        if (draft) await persist(draft);
                      }}
                    />
                  ),
                },
                approval: {
                  node: (
                    <ApprovalPanel
                      scenario={draft}
                      isDirty={isDirty}
                      separationOfDuties={settings.enforce_separation_of_duties}
                    />
                  ),
                },
                metadata: {
                  node: <MetadataPanel scenario={draft} onChange={onMetadataChange} />,
                },
              }}
            />
          </>
        )}
      </div>

      <NewScenarioDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={(id) => setSelectedId(id)}
      />
    </div>
  );
}
