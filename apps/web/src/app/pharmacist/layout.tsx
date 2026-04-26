"use client";

import type { ReactNode } from "react";

import { WorkspaceShell } from "@/components/workspace-shell";
import { PHARMACIST_CONSOLE_ROLES } from "@/lib/access";
import { pharmacistLinks } from "@/lib/navigation";

export default function PharmacistLayout({ children }: { children: ReactNode }) {
  return (
    <WorkspaceShell
      title="Pharmacist Workspace"
      description="Review prescription uploads, clarify unclear cases, and approve alternatives safely."
      nav={pharmacistLinks}
      allowedRoles={PHARMACIST_CONSOLE_ROLES}
      loginMessage="Pharmacist tools are available only after authenticated pharmacist or admin login."
      permissionMessage="Your current account does not have pharmacist review access."
    >
      {children}
    </WorkspaceShell>
  );
}
