import { Link, useRouterState } from "@tanstack/react-router";
import {
  BarChart3,
  ClipboardList,
  Database,
  LayoutDashboard,
  ScrollText,
  Settings,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { APP_VERSION } from "@/lib/version";

const groups = [
  {
    label: "Analyse",
    items: [
      { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard & Reporting" },
      { to: "/workspace", icon: Workflow, label: "Risk Assessment Workspace" },
      { to: "/sim-data", icon: Database, label: "Monte Carlo Simulation Data" },
      { to: "/register", icon: ClipboardList, label: "Quantified Exposure Register" },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/governance", icon: ShieldCheck, label: "Audit & Approvals" },
      { to: "/reports", icon: ScrollText, label: "Executive & Board Reports" },
    ],
  },
  {
    label: "System",
    items: [{ to: "/settings", icon: Settings, label: "Settings" }],
  },
] as const;

export function Sidebar() {
  const { location } = useRouterState();
  const path = location.pathname;
  return (
    <aside className="flex h-full w-[230px] flex-col border-r bg-surface">
      <div className="border-b px-5 py-4">
        <div className="flex items-center gap-2.5 font-semibold tracking-tight">
          <div className="h-5 w-5 rounded-md bg-gradient-to-br from-accent to-plum" />
          FORLAS
          <BarChart3 className="ml-auto h-4 w-4 text-muted" />
        </div>
        <div className="mt-1 text-[10.5px] uppercase tracking-wider text-muted">
          CRQ · Local
        </div>
      </div>
      <nav className="flex-1 overflow-auto px-2 py-3">
        {groups.map((g) => (
          <div key={g.label} className="mb-1">
            <div className="px-3 pt-3 pb-1.5 text-[10.5px] uppercase tracking-wider text-muted">
              {g.label}
            </div>
            {g.items.map(({ to, icon: Icon, label }) => {
              const active = path === to || path.startsWith(`${to}/`);
              return (
                <Link
                  key={to}
                  to={to}
                  className={cn(
                    "mb-0.5 flex items-center gap-2.5 rounded px-2.5 py-2 text-sm",
                    active
                      ? "bg-accent-soft text-accent font-semibold"
                      : "text-ink hover:bg-[var(--c-border-2)]",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="border-t px-4 py-3 text-[11px] text-muted">
        Build {APP_VERSION} · Offline
        <div className="mt-1">© 2026 Michael Walker</div>
      </div>
    </aside>
  );
}
