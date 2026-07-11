import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "@/components/common/AppShell";
import { NotFound } from "@/components/common/NotFound";
import { DashboardPage } from "@/pages/DashboardPage";
import { WorkspacePage } from "@/pages/WorkspacePage";
import { AnalysisEvidencePage } from "@/pages/AnalysisEvidencePage";
import { SimDataPage } from "@/pages/SimDataPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { GovernancePage } from "@/pages/GovernancePage";
import { SettingsPage } from "@/pages/SettingsPage";

const rootRoute = createRootRoute({ component: () => <Outlet /> });

const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  component: AppShell,
});

const indexRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/dashboard" });
  },
});

const dashboardRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/dashboard",
  component: DashboardPage,
});

const workspaceRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/workspace",
  component: WorkspacePage,
});

const analysisRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/analysis",
  component: AnalysisEvidencePage,
  // Deep-link support: /analysis?scenario=<public_id> preselects a scenario
  // (used by the "Analysis & evidence" shortcut in the Workspace).
  validateSearch: (search: Record<string, unknown>): { scenario?: string } => ({
    scenario: typeof search.scenario === "string" ? search.scenario : undefined,
  }),
});

const simDataRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/sim-data",
  component: SimDataPage,
});

const registerRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/register",
  component: RegisterPage,
});

const reportsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/reports",
  component: ReportsPage,
});

const governanceRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/governance",
  component: GovernancePage,
});

const settingsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/settings",
  component: SettingsPage,
});

const routeTree = rootRoute.addChildren([
  appRoute.addChildren([
    indexRoute,
    dashboardRoute,
    workspaceRoute,
    analysisRoute,
    simDataRoute,
    registerRoute,
    reportsRoute,
    governanceRoute,
    settingsRoute,
  ]),
]);

export const router = createRouter({ routeTree, defaultNotFoundComponent: NotFound });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
