"use client";

import type { ReactNode } from "react";

import { DashboardShell } from "@/components/dashboard-shell";
import { useAuthSession } from "@/hooks/use-auth-session";
import { canAccessRoles, filterLinksForRole } from "@/lib/access";

type WorkspaceShellProps = {
  title: string;
  description: string;
  nav: readonly { href: string; label: string }[];
  allowedRoles: readonly string[];
  loginMessage: string;
  permissionMessage: string;
  navAccessMap?: Record<string, readonly string[]>;
  children: ReactNode;
};

export function WorkspaceShell({
  title,
  description,
  nav,
  allowedRoles,
  loginMessage,
  permissionMessage,
  navAccessMap,
  children
}: WorkspaceShellProps) {
  const session = useAuthSession();

  if (!session.hydrated) {
    return (
      <div className="page-shell">
        <div className="empty-cart-box">
          <h2>Checking workspace access</h2>
          <p>Loading your saved session and role permissions.</p>
        </div>
      </div>
    );
  }

  if (!session.isAuthenticated) {
    return (
      <div className="page-shell">
        <div className="empty-cart-box">
          <h2>Login required</h2>
          <p>{loginMessage}</p>
        </div>
      </div>
    );
  }

  if (!canAccessRoles(session.user?.role, allowedRoles)) {
    return (
      <div className="page-shell">
        <div className="empty-cart-box">
          <h2>Permission required</h2>
          <p>{permissionMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <DashboardShell
      title={title}
      description={description}
      nav={navAccessMap ? filterLinksForRole(nav, session.user?.role, navAccessMap) : nav}
    >
      {children}
    </DashboardShell>
  );
}
