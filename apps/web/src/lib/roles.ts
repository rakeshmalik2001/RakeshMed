export type WorkspaceRoleRow = {
  typeOfUser: string;
  category: string;
  roleKey: string;
  roleLabel: string;
};

export const workspaceRoleRows: readonly WorkspaceRoleRow[] = [
  { typeOfUser: "Customer", category: "End User", roleKey: "customer", roleLabel: "Customer" },
  { typeOfUser: "Partner", category: "Business", roleKey: "vendor", roleLabel: "Vendor" },
  { typeOfUser: "Partner", category: "Business", roleKey: "vendor_staff", roleLabel: "Vendor Staff" },
  { typeOfUser: "Employee", category: "Healthcare", roleKey: "pharmacist", roleLabel: "Pharmacist" },
  { typeOfUser: "Employee", category: "Healthcare", roleKey: "doctor", roleLabel: "Doctor" },
  { typeOfUser: "Employee", category: "Operations", roleKey: "warehouse_operator", roleLabel: "Warehouse Operator" },
  { typeOfUser: "Employee", category: "Operations", roleKey: "delivery_agent", roleLabel: "Delivery Agent" },
  { typeOfUser: "Employee", category: "Operations", roleKey: "procurement_manager", roleLabel: "Procurement Manager" },
  { typeOfUser: "Employee", category: "Operations", roleKey: "operations_manager", roleLabel: "Operations Manager" },
  { typeOfUser: "Employee", category: "Support", roleKey: "support_agent", roleLabel: "Support Agent" },
  { typeOfUser: "Employee", category: "Finance", roleKey: "finance", roleLabel: "Finance" },
  { typeOfUser: "Employee", category: "Management", roleKey: "catalog_manager", roleLabel: "Catalog Manager" },
  { typeOfUser: "Employee", category: "Management", roleKey: "marketing_manager", roleLabel: "Marketing Manager" },
  { typeOfUser: "Employee", category: "Management", roleKey: "admin", roleLabel: "Admin" },
  { typeOfUser: "Employee", category: "Compliance", roleKey: "compliance_officer", roleLabel: "Compliance Officer" },
  { typeOfUser: "Employee", category: "Compliance", roleKey: "auditor", roleLabel: "Auditor" },
  { typeOfUser: "Employee", category: "General", roleKey: "viewer", roleLabel: "Viewer" },
  { typeOfUser: "System", category: "Security", roleKey: "security_admin", roleLabel: "Security Admin" },
  { typeOfUser: "System", category: "Core System", roleKey: "super_admin", roleLabel: "Super Admin" }
] as const;

export function serializeWorkspaceRoles(rows: readonly WorkspaceRoleRow[]) {
  return [
    ["Type of User", "Category", "Role"],
    ...rows.map((row) => [row.typeOfUser, row.category, row.roleLabel])
  ]
    .map((columns) => columns.join("\t"))
    .join("\n");
}
