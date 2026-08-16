import type { ReactNode } from "react";

import { NavSidebar } from "@/components/common/nav-sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-svh bg-canvas">
      <NavSidebar />
      <main className="flex-1 overflow-y-auto p-xl">{children}</main>
    </div>
  );
}
