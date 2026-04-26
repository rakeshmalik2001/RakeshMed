"use client";

import { useState } from "react";

import { getStoredAuthToken, getStoredAuthUser } from "@/lib/api";
import { serializeWorkspaceRoles, workspaceRoleRows } from "@/lib/roles";

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M9 7a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-7a2 2 0 0 1-2-2z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M6 15H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function AdminRolesPage() {
  const [copyMessage, setCopyMessage] = useState("");
  const isAuthenticated = Boolean(getStoredAuthToken());
  const role = getStoredAuthUser()?.role;

  if (!isAuthenticated) {
    return (
      <div className="empty-cart-box">
        <h2>Login required</h2>
        <p>Role definitions are available only after authenticated admin login.</p>
      </div>
    );
  }

  if (role !== "admin" && role !== "catalog_manager" && role !== "finance" && role !== "support_agent" && role !== "warehouse_operator") {
    return (
      <div className="empty-cart-box">
        <h2>Permission required</h2>
        <p>Your current account does not have access to the role directory.</p>
      </div>
    );
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(serializeWorkspaceRoles(workspaceRoleRows));
      setCopyMessage("Role list copied.");
      window.setTimeout(() => setCopyMessage(""), 2400);
    } catch {
      setCopyMessage("Clipboard unavailable on this browser.");
      window.setTimeout(() => setCopyMessage(""), 2400);
    }
  }

  return (
    <section className="soft-section">
      <div className="role-directory-shell">
        <div className="role-directory-header">
          <div>
            <h1 className="page-title">Role</h1>
            <p>These are the actual working roles assigned to users.</p>
          </div>
          <div className="role-directory-actions">
            {copyMessage ? <span className="role-copy-feedback">{copyMessage}</span> : null}
            <button type="button" className="role-copy-button" onClick={handleCopy} aria-label="Copy role table">
              <CopyIcon />
            </button>
          </div>
        </div>

        <div className="role-table-wrap">
          <table className="role-table">
            <thead>
              <tr>
                <th scope="col">Type of User</th>
                <th scope="col">Category</th>
                <th scope="col">Role</th>
              </tr>
            </thead>
            <tbody>
              {workspaceRoleRows.map((row) => (
                <tr key={row.roleKey}>
                  <td>{row.typeOfUser}</td>
                  <td>{row.category}</td>
                  <td>{row.roleLabel}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
