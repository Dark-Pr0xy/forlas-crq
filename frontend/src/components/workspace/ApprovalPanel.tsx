import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { apiErrorMessage } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAuth } from "@/store/auth";
import { useTransitionScenario, type ApprovalAction } from "@/lib/queries";
import type { ApprovalState, Role, ScenarioRead } from "@/types/api";

// Mirror the backend Role.rank ordering so the UI only offers actions the
// user can actually perform (backend still enforces).
const ROLE_RANK: Record<Role, number> = {
  readonly: 0,
  reviewer: 1,
  approver: 2,
  owner: 3,
};

interface ActionDef {
  action: ApprovalAction;
  label: string;
  role: Role;
  variant: "default" | "outline" | "danger";
}

// Legal transitions per state, matching app/services/approvals.py.
const ACTIONS: Record<ApprovalState, ActionDef[]> = {
  draft: [{ action: "submit_for_review", label: "Submit for review", role: "reviewer", variant: "default" }],
  in_review: [
    { action: "approve", label: "Approve", role: "approver", variant: "default" },
    { action: "reject", label: "Reject", role: "approver", variant: "danger" },
  ],
  approved: [{ action: "archive", label: "Archive", role: "owner", variant: "outline" }],
  archived: [{ action: "reopen", label: "Reopen", role: "owner", variant: "default" }],
};

const STATE_TONE: Record<ApprovalState, "neutral" | "amber" | "success" | "plum"> = {
  draft: "neutral",
  in_review: "amber",
  approved: "success",
  archived: "plum",
};

// Human labels — "in_review" reads as "Submitted" in the pipeline.
const STATE_LABEL: Record<ApprovalState, string> = {
  draft: "Draft",
  in_review: "Submitted",
  approved: "Approved",
  archived: "Archived",
};

// The linear pipeline shown as a stepper. Archived is a terminal offshoot and
// is surfaced separately (a badge) rather than as a stage.
const PIPELINE: ApprovalState[] = ["draft", "in_review", "approved"];

function StageStepper({ state }: { state: ApprovalState }) {
  const activeIndex = state === "archived" ? PIPELINE.length : PIPELINE.indexOf(state);
  return (
    <div className="flex items-center gap-1">
      {PIPELINE.map((s, i) => {
        const done = i < activeIndex;
        const current = i === activeIndex;
        return (
          <div key={s} className="flex items-center gap-1">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10.5px] font-medium",
                current
                  ? "bg-accent text-white"
                  : done
                    ? "bg-accent-soft text-accent"
                    : "bg-[var(--c-border-2)] text-muted",
              )}
            >
              {STATE_LABEL[s]}
            </span>
            {i < PIPELINE.length - 1 && (
              <span className={cn("h-px w-3", done ? "bg-accent" : "bg-[var(--c-border-2)]")} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function ApprovalPanel({
  scenario,
  isDirty,
  separationOfDuties = true,
}: {
  scenario: ScenarioRead;
  isDirty: boolean;
  separationOfDuties?: boolean;
}) {
  const user = useAuth((s) => s.user);
  const rank = user ? ROLE_RANK[user.role] : 0;
  const transition = useTransitionScenario(scenario.id);
  const [note, setNote] = useState("");

  const state = scenario.approval_state;
  const actions = ACTIONS[state] ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Approval
          <Badge tone={STATE_TONE[state]}>{STATE_LABEL[state]}</Badge>
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-2.5">
        <StageStepper state={state} />
        {isDirty && (
          <p className="text-[11px] text-amber">
            Save your changes before changing the approval state.
          </p>
        )}
        {state === "in_review" && separationOfDuties && (
          <p className="text-[11px] text-muted">
            Separation of duties: a user other than the submitter must approve this scenario.
          </p>
        )}
        {actions.length > 0 && (
          <Input
            placeholder="Note (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        )}
        <div className="flex flex-wrap gap-2">
          {actions.length === 0 ? (
            <p className="text-xs text-muted">No actions available in this state.</p>
          ) : (
            actions.map((a) => {
              const allowed = rank >= ROLE_RANK[a.role];
              return (
                <Button
                  key={a.action}
                  size="sm"
                  variant={a.variant}
                  disabled={!allowed || isDirty || transition.isPending}
                  title={allowed ? undefined : `Requires ${a.role} role or higher`}
                  onClick={() =>
                    transition.mutate(
                      { action: a.action, note: note || undefined },
                      { onSuccess: () => setNote("") },
                    )
                  }
                >
                  {a.label}
                </Button>
              );
            })
          )}
        </div>
        {transition.isError && (
          <p className="text-xs text-rose">{apiErrorMessage(transition.error)}</p>
        )}
      </CardBody>
    </Card>
  );
}
