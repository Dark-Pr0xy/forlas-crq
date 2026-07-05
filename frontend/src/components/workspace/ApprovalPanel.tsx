import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
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

export function ApprovalPanel({
  scenario,
  isDirty,
}: {
  scenario: ScenarioRead;
  isDirty: boolean;
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
          <Badge tone={STATE_TONE[state]}>{state.replace("_", " ")}</Badge>
        </CardTitle>
      </CardHeader>
      <CardBody className="space-y-2.5">
        {isDirty && (
          <p className="text-[11px] text-amber">
            Save your changes before changing the approval state.
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
          <p className="text-xs text-rose">
            Transition failed — you may not have permission for this action.
          </p>
        )}
      </CardBody>
    </Card>
  );
}
