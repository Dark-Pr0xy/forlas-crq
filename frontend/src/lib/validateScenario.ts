/**
 * Client-side pre-flight validation for a scenario draft.
 *
 * Mirrors the backend rules (app/schemas/scenario.py DistributionParam +
 * app/services/scenario.py analysis-lock) so the user is told *what* is wrong
 * or missing BEFORE a save/run round-trips and fails. If this returns an empty
 * list, the save should pass validation.
 */

import type {
  ApprovalState,
  DecompositionMode,
  DistributionParam,
  ReferenceLine,
  ScenarioInputs,
} from "@/types/api";

const REQUIRED: Record<DecompositionMode, (keyof ScenarioInputs)[]> = {
  lef: ["lef", "plm", "slp_prob", "slm"],
  "tef-vuln": ["tef", "vuln", "plm", "slp_prob", "slm"],
  full: ["tef", "tcap", "rs", "plm", "slp_prob", "slm"],
};

const LABELS: Record<string, string> = {
  lef: "Loss Event Frequency",
  tef: "Threat Event Frequency",
  vuln: "Vulnerability",
  tcap: "Threat Capability",
  rs: "Resistance Strength",
  plm: "Primary Loss Magnitude",
  slp_prob: "Secondary Loss Probability",
  slm: "Secondary Loss Magnitude",
};

function num(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function checkParam(label: string, p: DistributionParam | undefined | null): string[] {
  const out: string[] = [];
  if (!p || !p.type) {
    out.push(`${label}: choose a distribution.`);
    return out;
  }
  switch (p.type) {
    case "pert":
    case "triangular":
      if (!num(p.min) || !num(p.mode) || !num(p.max)) {
        out.push(`${label}: ${p.type} needs numeric Min, Mode and Max.`);
      } else if (!(p.min <= p.mode && p.mode <= p.max)) {
        out.push(
          `${label}: needs Min ≤ Mode ≤ Max (got ${p.min}, ${p.mode}, ${p.max}).`,
        );
      }
      break;
    case "uniform":
    case "normal":
    case "lognormal":
      if (!num(p.min) || !num(p.max)) {
        out.push(`${label}: ${p.type} needs numeric Min and Max.`);
      } else if (p.min > p.max) {
        out.push(`${label}: Min must be ≤ Max (got ${p.min} > ${p.max}).`);
      }
      if (p.type === "lognormal" && num(p.min) && p.min <= 0) {
        out.push(`${label}: lognormal P10 must be greater than 0.`);
      }
      break;
    case "beta":
      if (!num(p.alpha) || !num(p.beta)) {
        out.push(`${label}: beta needs numeric Alpha and Beta.`);
      }
      break;
    case "gamma":
      if (!num(p.shape)) {
        out.push(`${label}: gamma needs a numeric Shape.`);
      }
      break;
  }
  return out;
}

export function validateScenarioDraft(args: {
  mode: DecompositionMode;
  inputs: ScenarioInputs;
  referenceLines?: ReferenceLine[];
  approvalState?: ApprovalState;
  isDirty?: boolean;
}): string[] {
  const { mode, inputs, referenceLines, approvalState, isDirty } = args;
  const problems: string[] = [];

  const required = REQUIRED[mode] ?? [];
  for (const key of required) {
    problems.push(...checkParam(LABELS[key] ?? key, inputs?.[key]));
  }

  (referenceLines ?? []).forEach((l, i) => {
    if (!num(l?.value)) {
      problems.push(`Reference line ${i + 1} ("${l?.label ?? ""}"): needs a numeric value.`);
    }
  });

  // Analysis-lock: modelling fields can't change unless the scenario is draft.
  if (isDirty && approvalState && approvalState !== "draft") {
    problems.push(
      `Scenario is "${approvalState.replace("_", " ")}" — reopen it to draft before changing its model (inputs / mode / tolerance / reduction).`,
    );
  }

  return problems;
}
