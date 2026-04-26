export const storefrontLinks = [
  { href: "/", label: "Home" },
  { href: "/categories", label: "Categories" },
  { href: "/offers", label: "Offers" },
  { href: "/upload-prescription", label: "Upload Prescription" },
  { href: "/account/orders", label: "Orders" }
] as const;

export const adminLinks = [
  { href: "/admin/dashboard", label: "Dashboard" },
  { href: "/admin/roles", label: "Roles" },
  { href: "/admin/orders", label: "Orders" },
  { href: "/admin/delivery", label: "Delivery" },
  { href: "/admin/payments", label: "Payments" },
  { href: "/admin/reconciliation", label: "Reconciliation" },
  { href: "/admin/settlements", label: "Settlements" },
  { href: "/admin/products", label: "Products" },
  { href: "/admin/inventory", label: "Inventory" }
] as const;

export const pharmacistLinks = [
  { href: "/pharmacist", label: "Dashboard" },
  { href: "/pharmacist/prescriptions", label: "Review Queue" }
] as const;
