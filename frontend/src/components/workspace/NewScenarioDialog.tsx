import { useState } from "react";
import { Button } from "@/components/ui/Button";
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
import { useCreateScenario } from "@/lib/queries";
import type { DecompositionMode, ScenarioInputs } from "@/types/api";

const PRESETS: Record<"blank" | "ransomware" | "ddos" | "insider", () => ScenarioInputs> = {
  // Unassigned starting point — all fields zeroed so the scenario isn't
  // anchored to any template. Fill the inputs in the workspace before running.
  blank: () => ({
    tef: { type: "pert", min: 0, mode: 0, max: 0 },
    vuln: { type: "pert", min: 0, mode: 0, max: 0 },
    plm: { type: "pert", min: 0, mode: 0, max: 0 },
    slp_prob: { type: "pert", min: 0, mode: 0, max: 0 },
    slm: { type: "pert", min: 0, mode: 0, max: 0 },
  }),
  ransomware: () => ({
    tef: { type: "pert", min: 1, mode: 4, max: 12 },
    vuln: { type: "pert", min: 0.05, mode: 0.25, max: 0.6 },
    plm: { type: "lognormal", min: 200_000, max: 6_000_000 },
    slp_prob: { type: "pert", min: 0.3, mode: 0.55, max: 0.85 },
    slm: { type: "lognormal", min: 100_000, max: 8_000_000 },
  }),
  ddos: () => ({
    tef: { type: "pert", min: 4, mode: 12, max: 30 },
    vuln: { type: "pert", min: 0.1, mode: 0.3, max: 0.6 },
    plm: { type: "lognormal", min: 10_000, max: 400_000 },
    slp_prob: { type: "pert", min: 0.1, mode: 0.25, max: 0.5 },
    slm: { type: "lognormal", min: 5_000, max: 300_000 },
  }),
  insider: () => ({
    tef: { type: "pert", min: 0.5, mode: 1.5, max: 4 },
    vuln: { type: "pert", min: 0.05, mode: 0.25, max: 0.6 },
    plm: { type: "lognormal", min: 100_000, max: 3_000_000 },
    slp_prob: { type: "pert", min: 0.1, mode: 0.4, max: 0.8 },
    slm: { type: "pert", min: 25_000, mode: 150_000, max: 2_000_000 },
  }),
};

interface NewScenarioDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (id: string) => void;
}

export function NewScenarioDialog({ open, onOpenChange, onCreated }: NewScenarioDialogProps) {
  const [name, setName] = useState("");
  const [bu, setBu] = useState("");
  const [tolerance, setTolerance] = useState(1_000_000);
  const [preset, setPreset] = useState<keyof typeof PRESETS>("blank");
  const [mode, setMode] = useState<DecompositionMode>("tef-vuln");
  const createMutation = useCreateScenario();

  async function submit() {
    if (!name.trim()) return;
    const inputs = PRESETS[preset]();
    const scn = await createMutation.mutateAsync({
      name: name.trim(),
      business_unit: bu.trim() || undefined,
      tolerance,
      mode,
      inputs,
    });
    onOpenChange(false);
    setName("");
    setBu("");
    setTolerance(1_000_000);
    onCreated(scn.id);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New scenario</DialogTitle>
          <DialogDescription>
            Pick a preset and tune from the Workspace once it&apos;s open.
          </DialogDescription>
        </DialogHeader>
        <div className="mt-3 space-y-3">
          <div className="space-y-1">
            <Label>Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Ransomware on production ERP"
              autoFocus
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label>Business unit</Label>
              <Input value={bu} onChange={(e) => setBu(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Tolerance (AUD)</Label>
              <Input
                type="number"
                value={tolerance}
                onChange={(e) => setTolerance(Number(e.target.value))}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label>Starting point</Label>
              <Select
                value={preset}
                onChange={(e) => setPreset(e.target.value as keyof typeof PRESETS)}
              >
                <option value="blank">Blank (unassigned)</option>
                <option value="ransomware">Ransomware template</option>
                <option value="ddos">DDoS template</option>
                <option value="insider">Insider exfiltration template</option>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Mode</Label>
              <Select
                value={mode}
                onChange={(e) => setMode(e.target.value as DecompositionMode)}
              >
                <option value="tef-vuln">TEF × Vulnerability</option>
                <option value="lef">Direct LEF</option>
                <option value="full">Full decomposition</option>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!name.trim() || createMutation.isPending} onClick={submit}>
            {createMutation.isPending ? "Creating…" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
