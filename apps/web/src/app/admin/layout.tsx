"use client";

import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/workspace-shell";
import { ADMIN_CONSOLE_ROLES, ADMIN_PAGE_ACCESS } from "@/lib/access";
import { adminLinks } from "@/lib/navigation";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <WorkspaceShell
      title="Admin Console"
      description="Manage products, stock, operations, and pharmacy business controls."
      nav={adminLinks}
      allowedRoles={ADMIN_CONSOLE_ROLES}
      navAccessMap={ADMIN_PAGE_ACCESS}
      loginMessage="Admin operations are available only after authenticated back-office login."
      permissionMessage="Your current account does not have access to the admin console."
    >
      {children}
    </WorkspaceShell>
  );
}
