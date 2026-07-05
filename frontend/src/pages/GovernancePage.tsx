import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader, CardHint, CardTitle } from "@/components/ui/Card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { fmt } from "@/lib/format";

interface AuditEntry {
  id: number;
  actor_label: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  summary: string;
  created_at: string;
}

interface ApprovalRequest {
  id: string;
  entity_type: string;
  entity_id: number;
  state: string;
  requested_by_user_id: number;
  decided_by_user_id: number | null;
  decided_at: string | null;
  request_note: string | null;
  decision_note: string | null;
  created_at: string;
}

interface ReviewItem {
  scenario_id: string;
  name: string;
  business_unit: string | null;
  owner_label: string | null;
  approval_state: string;
  assessment_date: string | null;
  review_date: string | null;
  overdue: boolean;
  days_until: number | null;
}

function reviewStatusText(item: ReviewItem): string {
  if (item.days_until == null) return "—";
  if (item.days_until < 0) return `${Math.abs(item.days_until)}d overdue`;
  if (item.days_until === 0) return "due today";
  return `in ${item.days_until}d`;
}

export function GovernancePage() {
  const [tab, setTab] = useState("audit");

  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList>
        <TabsTrigger value="audit">Audit log</TabsTrigger>
        <TabsTrigger value="approvals">Approvals</TabsTrigger>
        <TabsTrigger value="reviews">Reviews</TabsTrigger>
      </TabsList>
      <TabsContent value="audit">
        <AuditTab />
      </TabsContent>
      <TabsContent value="approvals">
        <ApprovalsTab />
      </TabsContent>
      <TabsContent value="reviews">
        <ReviewsTab />
      </TabsContent>
    </Tabs>
  );
}

function AuditTab() {
  const { data, isLoading } = useQuery<AuditEntry[]>({
    queryKey: ["audit"],
    queryFn: () => api.get<AuditEntry[]>("/api/governance/audit?limit=200"),
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit log</CardTitle>
        <CardHint>Append-only · most recent first</CardHint>
      </CardHeader>
      <CardBody>
        {isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted">
                  <th className="py-2 pr-2">When</th>
                  <th className="py-2 pr-2">Actor</th>
                  <th className="py-2 pr-2">Action</th>
                  <th className="py-2 pr-2">Entity</th>
                  <th className="py-2 pr-2">Summary</th>
                </tr>
              </thead>
              <tbody>
                {(data ?? []).map((row) => (
                  <tr key={row.id} className="border-b border-[var(--c-border-2)]">
                    <td className="py-1.5 pr-2 font-mono text-[11.5px] text-muted">
                      {fmt.date(row.created_at)}
                    </td>
                    <td className="py-1.5 pr-2">{row.actor_label ?? "—"}</td>
                    <td className="py-1.5 pr-2">
                      <Badge tone="accent">{row.action}</Badge>
                    </td>
                    <td className="py-1.5 pr-2 text-muted">
                      {row.entity_type}
                      {row.entity_id ? ` · ${row.entity_id}` : ""}
                    </td>
                    <td className="py-1.5 pr-2 text-ink">{row.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function ApprovalsTab() {
  const { data, isLoading } = useQuery<ApprovalRequest[]>({
    queryKey: ["approvals"],
    queryFn: () => api.get<ApprovalRequest[]>("/api/governance/approvals?limit=100"),
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle>Approval history</CardTitle>
        <CardHint>Every state transition recorded</CardHint>
      </CardHeader>
      <CardBody>
        {isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : (data?.length ?? 0) === 0 ? (
          <p className="text-sm text-muted">
            No approval transitions yet. Submit a scenario from the Workspace to start.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs uppercase tracking-wide text-muted">
                <th className="py-2 pr-2">When</th>
                <th className="py-2 pr-2">Entity</th>
                <th className="py-2 pr-2">State</th>
                <th className="py-2 pr-2">Note</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((row) => (
                <tr key={row.id} className="border-b border-[var(--c-border-2)]">
                  <td className="py-1.5 pr-2 font-mono text-[11.5px] text-muted">
                    {fmt.date(row.created_at)}
                  </td>
                  <td className="py-1.5 pr-2">
                    {row.entity_type} · {row.entity_id}
                  </td>
                  <td className="py-1.5 pr-2">
                    <Badge
                      tone={
                        row.state === "approved"
                          ? "success"
                          : row.state === "in_review"
                            ? "amber"
                            : row.state === "archived"
                              ? "plum"
                              : "neutral"
                      }
                    >
                      {row.state}
                    </Badge>
                  </td>
                  <td className="py-1.5 pr-2 text-muted">
                    {row.decision_note ?? row.request_note ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardBody>
    </Card>
  );
}

function ReviewsTab() {
  const { data, isLoading } = useQuery<ReviewItem[]>({
    queryKey: ["reviews"],
    queryFn: () => api.get<ReviewItem[]>("/api/governance/reviews"),
  });

  const dated = (data ?? []).filter((r) => r.review_date);
  const overdue = dated.filter((r) => r.overdue);
  const undatedCount = (data ?? []).length - dated.length;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
      <Card>
        <CardHeader>
          <CardTitle>Scenario reviews</CardTitle>
          <CardHint>Driven by each scenario&apos;s review date</CardHint>
        </CardHeader>
        <CardBody>
          {isLoading ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : dated.length === 0 ? (
            <p className="text-sm text-muted">
              No review dates set yet. Set one per scenario in the Workspace → Scenario
              metadata → <span className="font-medium">Review date</span>, and it will
              appear here as current or overdue.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted">
                  <th className="py-2 pr-2">Scenario</th>
                  <th className="py-2 pr-2">Business unit</th>
                  <th className="py-2 pr-2">Review date</th>
                  <th className="py-2 pr-2">When</th>
                  <th className="py-2 pr-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {dated.map((r) => (
                  <tr key={r.scenario_id} className="border-b border-[var(--c-border-2)]">
                    <td className="py-1.5 pr-2 text-ink">{r.name}</td>
                    <td className="py-1.5 pr-2 text-muted">{r.business_unit ?? "—"}</td>
                    <td className="py-1.5 pr-2 font-mono text-[11.5px]">{r.review_date}</td>
                    <td className="py-1.5 pr-2 font-mono text-[11.5px] text-muted">
                      {reviewStatusText(r)}
                    </td>
                    <td className="py-1.5 pr-2">
                      <Badge tone={r.overdue ? "rose" : "success"}>
                        {r.overdue ? "overdue" : "current"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {undatedCount > 0 && (
            <p className="mt-3 text-[11px] text-muted">
              {undatedCount} scenario{undatedCount === 1 ? "" : "s"} without a review date.
            </p>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Overdue</CardTitle>
          <CardHint>Past their review date</CardHint>
        </CardHeader>
        <CardBody>
          {overdue.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              All reviews up to date.
            </div>
          ) : (
            <ul className="space-y-1.5 text-sm">
              {overdue.map((r) => (
                <li
                  key={r.scenario_id}
                  className="flex items-baseline justify-between border-b border-[var(--c-border-2)] pb-1.5"
                >
                  <span className="truncate pr-2">{r.name}</span>
                  <span className="whitespace-nowrap font-mono text-[11.5px] text-rose">
                    {reviewStatusText(r)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
