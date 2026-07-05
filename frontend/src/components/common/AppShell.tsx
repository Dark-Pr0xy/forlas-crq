import { Outlet } from "@tanstack/react-router";
import { Sidebar } from "@/components/common/Sidebar";
import { TopBar } from "@/components/common/TopBar";

export function AppShell() {
  // Flex (not grid) for the outer so we can apply `min-h-0` to <main> and let
  // the inner `flex-1 overflow-auto` actually scroll. Without min-h-0 the flex
  // child's implicit min-height:auto stops it shrinking below its content,
  // overflow-auto never activates, and the outer `overflow-hidden` clips it.
  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <div className="w-[230px] flex-shrink-0">
        <Sidebar />
      </div>
      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        <TopBar />
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
