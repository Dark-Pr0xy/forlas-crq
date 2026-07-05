import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "@/components/common/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { WorkspacePage } from "@/pages/WorkspacePage";
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
    simDataRoute,
    registerRoute,
    reportsRoute,
    governanceRoute,
    settingsRoute,
  ]),
]);

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center">
      <div className="text-3xl font-semibold text-ink">404</div>
      <p className="text-sm text-muted">This page doesn&apos;t exist.</p>
      <a href="/dashboard" className="text-sm text-accent hover:underline">
        Back to dashboard
      </a>
    </div>
  );
}

export const router = createRouter({ routeTree, defaultNotFoundComponent: NotFound });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
