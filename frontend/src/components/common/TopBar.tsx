import { useRouterState } from "@tanstack/react-router";
import { LogOut, Moon, Sun, User } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, setSessionToken } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useAuth } from "@/store/auth";
import { useTheme } from "@/store/theme";
import type { AppSettings } from "@/types/api";

const PAGE_TITLES: Record<string, { title: string; crumb: string }> = {
  "/dashboard": { title: "Dashboard & Reporting", crumb: "Portfolio exposure overview" },
  "/workspace": { title: "Risk Assessment Workspace", crumb: "Build and tune scenarios" },
  "/sim-data": { title: "Monte Carlo Simulation Data", crumb: "Raw iteration data" },
  "/register": { title: "Quantified Exposure Register", crumb: "Portfolio-wide exposures" },
  "/reports": { title: "Reports", crumb: "Executive · Board · Exports" },
  "/governance": { title: "Governance", crumb: "Audit log · Approvals · Reviews" },
  "/settings": { title: "Settings", crumb: "Application configuration" },
};

export function TopBar() {
  const { location } = useRouterState();
  const meta = PAGE_TITLES[location.pathname] ?? PAGE_TITLES["/dashboard"];
  const user = useAuth((s) => s.user);
  const clear = useAuth((s) => s.clear);
  const theme = useTheme((s) => s.theme);
  const toggleTheme = useTheme((s) => s.toggle);
  const qc = useQueryClient();

  const { data: settings } = useQuery<AppSettings>({
    queryKey: ["settings"],
    queryFn: () => api.get<AppSettings>("/api/settings"),
  });

  const logout = useMutation({
    mutationFn: () => api.post("/api/auth/logout"),
    onSuccess: () => {
      setSessionToken(null);
      clear();
      qc.clear();
    },
  });

  return (
    <header className="flex h-[54px] items-center gap-4 border-b bg-surface px-6">
      <div>
        <h1 className="text-[15px] font-semibold leading-none">{meta.title}</h1>
        <div className="mt-1 text-xs text-muted">{meta.crumb}</div>
      </div>
      <div className="flex-1" />
      <Badge tone="neutral" className="font-mono">
        Seed: {settings?.seed ?? "—"}
      </Badge>
      <Badge tone="neutral" className="font-mono">
        Iterations: {settings ? settings.iterations.toLocaleString() : "—"}
      </Badge>
      <div className="flex items-center gap-2 border-l pl-4">
        <User className="h-4 w-4 text-muted" />
        <span className="text-xs">
          <span className="font-medium text-ink">{user?.display_name}</span>{" "}
          <span className="text-muted">· {user?.role}</span>
        </span>
        <Button
          size="icon"
          variant="ghost"
          onClick={() => toggleTheme()}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={() => logout.mutate()}
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
