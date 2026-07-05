import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import type { ScenarioRead } from "@/types/api";

export interface MetadataPanelChanges {
  business_unit?: string;
  owner_label?: string;
  scenario_type?: string;
  benchmark_group?: string;
  tags?: string[];
  assessment_date?: string;
  review_date?: string;
  version_label?: string;
  tolerance?: number;
  notes?: string;
}

interface MetadataPanelProps {
  scenario: ScenarioRead;
  onChange: (patch: MetadataPanelChanges) => void;
}

export function MetadataPanel({ scenario, onChange }: MetadataPanelProps) {
  const [tagInput, setTagInput] = useState((scenario.tags ?? []).join(", "));
  useEffect(() => setTagInput((scenario.tags ?? []).join(", ")), [scenario.id]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scenario metadata</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3.5">
        <Field label="Business unit">
          <Input
            value={scenario.business_unit ?? ""}
            onChange={(e) => onChange({ business_unit: e.target.value })}
          />
        </Field>
        <Field label="Scenario owner">
          <Input
            value={scenario.owner_label ?? ""}
            onChange={(e) => onChange({ owner_label: e.target.value })}
          />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Scenario type">
            <Input
              value={scenario.scenario_type ?? ""}
              onChange={(e) => onChange({ scenario_type: e.target.value })}
            />
          </Field>
          <Field label="Version">
            <Input
              value={scenario.version_label}
              onChange={(e) => onChange({ version_label: e.target.value })}
            />
          </Field>
        </div>
        <Field label="Benchmark group">
          <Input
            value={scenario.benchmark_group ?? ""}
            onChange={(e) => onChange({ benchmark_group: e.target.value })}
          />
        </Field>
        <Field label="Tolerance (AUD)">
          <Input
            type="number"
            value={scenario.tolerance ?? 0}
            onChange={(e) => onChange({ tolerance: Number(e.target.value) })}
          />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Assessment date">
            <Input
              type="date"
              value={scenario.assessment_date ?? ""}
              onChange={(e) => onChange({ assessment_date: e.target.value })}
            />
          </Field>
          <Field label="Review date">
            <Input
              type="date"
              value={scenario.review_date ?? ""}
              onChange={(e) => onChange({ review_date: e.target.value })}
            />
          </Field>
        </div>
        <Field label="Tags (comma separated)">
          <Input
            value={tagInput}
            onChange={(e) => {
              setTagInput(e.target.value);
              const tags = e.target.value
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean);
              onChange({ tags });
            }}
          />
          {(scenario.tags ?? []).length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {scenario.tags.map((t) => (
                <Badge key={t} tone="neutral">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </Field>
        <Field label="Notes">
          <Textarea
            value={scenario.notes ?? ""}
            onChange={(e) => onChange({ notes: e.target.value })}
          />
        </Field>
      </CardBody>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
