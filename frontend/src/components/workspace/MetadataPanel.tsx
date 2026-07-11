import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import { useAddScenarioType, useScenarioTypes } from "@/lib/queries";
import type { ScenarioRead } from "@/types/api";

export interface MetadataPanelChanges {
  business_unit?: string;
  owner_label?: string;
  scenario_type?: string;
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
  // Reset the free-text tag field only when switching scenarios; while typing,
  // scenario.tags changes on every keystroke and must NOT clobber the input.
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
            <ScenarioTypeSelect
              value={scenario.scenario_type ?? ""}
              onChange={(v) => onChange({ scenario_type: v })}
            />
          </Field>
          <Field label="Version">
            <Input
              value={scenario.version_label}
              onChange={(e) => onChange({ version_label: e.target.value })}
            />
          </Field>
        </div>
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

const ADD_SENTINEL = "__add_new_type__";

/** Preset scenario-type picker with an inline "add your own" flow. */
function ScenarioTypeSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const { data } = useScenarioTypes();
  const add = useAddScenarioType();
  const [adding, setAdding] = useState(false);
  const [newType, setNewType] = useState("");

  const types = data?.types ?? [];
  // Keep a legacy/current value visible even if it's not in the known list.
  const options =
    value && !types.some((t) => t.toLowerCase() === value.toLowerCase())
      ? [value, ...types]
      : types;

  function commit() {
    const name = newType.trim();
    if (!name) return;
    add.mutate(name, {
      onSuccess: () => {
        onChange(name);
        setAdding(false);
        setNewType("");
      },
    });
  }

  function cancel() {
    setAdding(false);
    setNewType("");
  }

  if (adding) {
    return (
      <div className="flex gap-1">
        <Input
          autoFocus
          value={newType}
          placeholder="New type"
          onChange={(e) => setNewType(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commit();
            } else if (e.key === "Escape") {
              cancel();
            }
          }}
        />
        <Button size="sm" onClick={commit} disabled={!newType.trim() || add.isPending}>
          Add
        </Button>
        <Button size="sm" variant="ghost" onClick={cancel} title="Cancel">
          ✕
        </Button>
      </div>
    );
  }

  return (
    <Select
      value={value}
      onChange={(e) => {
        if (e.target.value === ADD_SENTINEL) {
          setAdding(true);
          return;
        }
        onChange(e.target.value);
      }}
    >
      <option value="">Unspecified</option>
      {options.map((t) => (
        <option key={t} value={t}>
          {t}
        </option>
      ))}
      <option value={ADD_SENTINEL}>＋ Add new type…</option>
    </Select>
  );
}
