export const ADMIN_CONSOLE_ROLES = [
  "admin",
  "catalog_manager",
  "finance",
  "support_agent",
  "warehouse_operator"
] as const;

export const PHARMACIST_CONSOLE_ROLES = ["admin", "pharmacist"] as const;

export const ADMIN_PAGE_ACCESS: Record<string, readonly string[]> = {
  "/admin/dashboard": ADMIN_CONSOLE_ROLES,
  "/admin/roles": ADMIN_CONSOLE_ROLES,
  "/admin/orders": ADMIN_CONSOLE_ROLES,
  "/admin/delivery": ["admin", "warehouse_operator", "support_agent", "finance"],
  "/admin/payments": ["admin", "finance", "support_agent"],
  "/admin/reconciliation": ["admin", "finance"],
  "/admin/settlements": ["admin", "finance"],
  "/admin/products": ["admin", "catalog_manager", "support_agent"],
  "/admin/inventory": ["admin", "catalog_manager", "warehouse_operator", "support_agent"]
};

export function canAccessRoles(role: string | null | undefined, allowedRoles: readonly string[]) {
  return Boolean(role && allowedRoles.includes(role));
}

export function filterLinksForRole<T extends { href: string }>(
  links: readonly T[],
  role: string | null | undefined,
  accessMap: Record<string, readonly string[]>
) {
  return links.filter((link) => {
    const allowedRoles = accessMap[link.href];
    if (!allowedRoles) {
      return true;
    }

    return canAccessRoles(role, allowedRoles);
  });
}
