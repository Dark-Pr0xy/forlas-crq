import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Download, ExternalLink, Presentation } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { fmt } from "@/lib/format";
import { useScenarios } from "@/lib/queries";
import { api, saveBlob } from "@/lib/api";
import { PresentationMode } from "@/components/reports/PresentationMode";

type Kind = "executive" | "board";
type Scope = "portfolio" | "individual" | "both";

interface Payload {
  kind: Kind;
  scope: Scope;
  scenario_ids: string[];
  appetite: number | null;
}

export function ReportsPage() {
  const { data: scenarios } = useScenarios();
  const [kind, setKind] = useState<Kind>("executive");
  const [scope, setScope] = useState<Scope>("both");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [appetite, setAppetite] = useState<number | null>(null);
  const [presentationOpen, setPresentationOpen] = useState(false);
  const [presentationIds, setPresentationIds] = useState<string[]>([]);
  const [initialised, setInitialised] = useState(false);
  const [htmlPreview, setHtmlPreview] = useState<string | null>(null);

  // Default to "all selected" on first load — but treat empty set as honestly
  // empty afterwards (so Select None actually deselects everything).
  useEffect(() => {
    if (!initialised && scenarios && scenarios.length > 0) {
      setSelectedIds(new Set(scenarios.map((s) => s.id)));
      setInitialised(true);
    }
  }, [scenarios, initialised]);

  const total = scenarios?.length ?? 0;
  const selectedCount = selectedIds.size;
  const allSelected = total > 0 && selectedCount === total;
  const noneSelected = selectedCount === 0;

  const effective: Payload = useMemo(
    () => ({
      kind,
      scope,
      scenario_ids: Array.from(selectedIds),
      appetite,
    }),
    [kind, scope, selectedIds, appetite],
  );

  function selectAll() {
    if (!scenarios) return;
    setSelectedIds(new Set(scenarios.map((s) => s.id)));
  }

  function selectNone() {
    setSelectedIds(new Set());
  }

  function toggle(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const htmlMutation = useMutation({
    mutationFn: () => api.text("/api/reports/html", { method: "POST", body: effective }),
    // Render inline in an in-app modal. The desktop WebView blocks
    // window.open pop-ups, so we preview via an iframe instead and offer a
    // Save-to-file action.
    onSuccess: (html) => setHtmlPreview(html),
  });

  const docxMutation = useMutation({
    mutationFn: () => api.blob("/api/reports/docx", { method: "POST", body: effective }),
    onSuccess: (blob) => {
      saveBlob(blob, `forlas_${effective.kind}_report.docx`);
    },
  });

  function openPresentation() {
    if (selectedCount === 0) return;
    setPresentationIds(Array.from(selectedIds));
    setPresentationOpen(true);
  }

  const disabled = noneSelected;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader>
            <CardTitle>Scenario selection</CardTitle>
            <CardHint>
              {allSelected
                ? `All ${total} selected`
                : noneSelected
                  ? "None selected"
                  : `${selectedCount} of ${total} selected`}
            </CardHint>
          </CardHeader>
          <CardBody>
            <div className="mb-2 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={selectAll}
                disabled={allSelected}
              >
                Select all
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={selectNone}
                disabled={noneSelected}
              >
                Select none
              </Button>
            </div>
            <div className="max-h-[420px] divide-y overflow-auto rounded border">
              {(scenarios ?? []).map((s) => {
                const checked = selectedIds.has(s.id);
                return (
                  <label
                    key={s.id}
                    className="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-[var(--c-border-2)]"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(s.id)}
                      className="accent-[#7A92F4]"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{s.name}</div>
                      <div className="truncate text-[11px] text-muted">
                        {s.business_unit ?? "—"} · tol {fmt.money(s.tolerance)}
                      </div>
                    </div>
                    <Badge tone="accent">{s.mode}</Badge>
                  </label>
                );
              })}
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Report options</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3">
            <div className="space-y-1">
              <Label>Report kind</Label>
              <Select value={kind} onChange={(e) => setKind(e.target.value as Kind)}>
                <option value="executive">Executive Summary</option>
                <option value="board">Board Pack</option>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Scope</Label>
              <Select value={scope} onChange={(e) => setScope(e.target.value as Scope)}>
                <option value="portfolio">Portfolio aggregate only</option>
                <option value="individual">Individual scenarios</option>
                <option value="both">Both — aggregate then per-scenario</option>
              </Select>
              <p className="text-[11px] text-muted">
                Board Pack always renders per-scenario detail regardless of scope.
              </p>
            </div>
            <div className="space-y-1">
              <Label>Risk appetite (AUD, optional)</Label>
              <Input
                type="number"
                value={appetite ?? ""}
                onChange={(e) =>
                  setAppetite(e.target.value ? Number(e.target.value) : null)
                }
              />
            </div>
            <div className="space-y-2 pt-2">
              <Button
                className="w-full"
                onClick={() => htmlMutation.mutate()}
                disabled={htmlMutation.isPending || disabled}
              >
                <ExternalLink className="h-4 w-4" />
                {htmlMutation.isPending ? "Rendering…" : "Open HTML report"}
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => docxMutation.mutate()}
                disabled={docxMutation.isPending || disabled}
              >
                <Download className="h-4 w-4" />
                {docxMutation.isPending ? "Generating…" : "Download DOCX"}
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={openPresentation}
                disabled={disabled}
              >
                <Presentation className="h-4 w-4" />
                Presentation mode
              </Button>
              {disabled && (
                <p className="text-xs text-amber">
                  Select at least one scenario to generate a report.
                </p>
              )}
              {(htmlMutation.isError || docxMutation.isError) && (
                <p className="text-xs text-rose">
                  Report generation failed — confirm at least one selected scenario has been simulated.
                </p>
              )}
            </div>
          </CardBody>
        </Card>
      </div>

      {presentationOpen && (
        <PresentationMode
          scenarioIds={presentationIds}
          onClose={() => setPresentationOpen(false)}
        />
      )}

      {htmlPreview !== null && (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-black/50 p-4"
          onClick={() => setHtmlPreview(null)}
        >
          <div
            className="mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-lg bg-surface shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b px-4 py-2">
              <div className="text-sm font-semibold">
                Report preview · {kind === "board" ? "Board Pack" : "Executive Summary"}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    saveBlob(
                      new Blob([htmlPreview], { type: "text/html" }),
                      `forlas_${kind}_report.html`,
                    )
                  }
                >
                  <Download className="h-4 w-4" />
                  Save HTML
                </Button>
                <Button size="sm" onClick={() => setHtmlPreview(null)}>
                  Close
                </Button>
              </div>
            </div>
            <iframe
              title="Report preview"
              srcDoc={htmlPreview}
              sandbox="allow-same-origin"
              className="h-full w-full flex-1 bg-white"
            />
          </div>
        </div>
      )}
    </div>
  );
}
