"use client";

import { useMemo } from "react";

import { useAuthSession } from "@/hooks/use-auth-session";
import { getRoleDashboardConfig } from "@/lib/role-dashboard";

import { RoleDashboardView } from "./role-dashboard-view";

export function WorkspaceRoleDashboardClient({ roleParam }: { roleParam: string }) {
  const session = useAuthSession();
  const config = useMemo(() => getRoleDashboardConfig(roleParam), [roleParam]);

  if (!config) {
    return (
      <main className="page-shell">
        <div className="empty-cart-box">
          <h2>Dashboard unavailable</h2>
          <p>This role does not have a configured dashboard yet.</p>
        </div>
      </main>
    );
  }

  if (!session.hydrated) {
    return (
      <main className="page-shell">
        <div className="empty-cart-box">
          <h2>Checking dashboard access</h2>
          <p>Loading your saved session and role permissions.</p>
        </div>
      </main>
    );
  }

  if (!session.isAuthenticated) {
    return (
      <main className="page-shell">
        <div className="empty-cart-box">
          <h2>Login required</h2>
          <p>This workspace dashboard is available only after authenticated login.</p>
        </div>
      </main>
    );
  }

  if (session.user?.role !== roleParam && session.user?.role !== "super_admin") {
    return (
      <main className="page-shell">
        <div className="empty-cart-box">
          <h2>Permission required</h2>
          <p>Your current account does not have access to this role-specific dashboard.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="soft-section">
        <RoleDashboardView config={config} />
      </section>
    </main>
  );
}
