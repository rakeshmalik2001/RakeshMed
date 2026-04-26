import type { Route } from "next";

export type RoleDashboardCard = {
  label: string;
  value: string;
  meta: string;
};

export type RoleDashboardPanel = {
  title: string;
  body: string;
  href?: Route;
  hrefLabel?: string;
};

export type RoleDashboardConfig = {
  role: string;
  eyebrow: string;
  title: string;
  intro: string;
  summaryCards: readonly RoleDashboardCard[];
  workstreams: readonly string[];
  panels: readonly RoleDashboardPanel[];
};

function makeConfig(
  role: string,
  eyebrow: string,
  title: string,
  intro: string,
  summaryCards: readonly RoleDashboardCard[],
  workstreams: readonly string[],
  panels: readonly RoleDashboardPanel[]
): RoleDashboardConfig {
  return {
    role,
    eyebrow,
    title,
    intro,
    summaryCards,
    workstreams,
    panels
  };
}

export const roleDashboardConfigs: Record<string, RoleDashboardConfig> = {
  customer: makeConfig(
    "customer",
    "Customer Dashboard",
    "Customer account dashboard",
    "Track prescriptions, orders, saved addresses, and notifications from one customer workspace.",
    [
      { label: "Primary surface", value: "Account", meta: "Orders, profile, and saved delivery details" },
      { label: "Main objective", value: "Order confidence", meta: "See status and complete repeat purchase tasks quickly" },
      { label: "Shared inputs", value: "Storefront + Rx", meta: "Search, upload, checkout, and order history stay connected" }
    ],
    ["Monitor recent order updates", "Upload and track prescriptions", "Manage addresses, profile, and payment preferences"],
    [
      { title: "Order history", body: "Review placed orders, payment state, and delivery progress.", href: "/account/orders", hrefLabel: "Open orders" },
      { title: "Prescription uploads", body: "Upload files and track pharmacist review decisions.", href: "/account/prescriptions", hrefLabel: "Open prescriptions" },
      { title: "Browse medicines", body: "Continue shopping from the storefront when you need a refill.", href: "/search", hrefLabel: "Search catalog" }
    ]
  ),
  vendor: makeConfig(
    "vendor",
    "Vendor Dashboard",
    "Vendor dashboard",
    "A landing page for partners responsible for inventory readiness, catalog coverage, and store coordination.",
    [
      { label: "Primary surface", value: "Vendor workspace", meta: "Partner-facing operations and fulfillment oversight" },
      { label: "Main objective", value: "Stock readiness", meta: "Keep listings available and handoffs predictable" },
      { label: "Shared inputs", value: "Catalog + orders", meta: "Coordinate with procurement, warehouse, and dispatch" }
    ],
    ["Review stock posture and replenishment needs", "Coordinate catalog readiness for partner assortment", "Watch order readiness before fulfillment handoff"],
    [
      { title: "Storefront context", body: "Check how products and categories appear on the customer side.", href: "/search", hrefLabel: "View storefront" },
      { title: "Partner focus", body: "Treat this dashboard as the vendor landing page for upcoming partner tooling." },
      { title: "Workflow boundaries", body: "Use this dashboard to separate partner work from warehouse, support, and admin-facing landings." }
    ]
  ),
  vendor_staff: makeConfig(
    "vendor_staff",
    "Vendor Staff Dashboard",
    "Vendor staff dashboard",
    "A lighter partner workspace for day-to-day catalog maintenance, order follow-up, and store support coordination.",
    [
      { label: "Primary surface", value: "Partner support", meta: "Execution help for vendor-led operations" },
      { label: "Main objective", value: "Day-to-day upkeep", meta: "Keep routine partner tasks moving without escalation" },
      { label: "Shared inputs", value: "Catalog + support", meta: "Follow internal processes set by vendor managers" }
    ],
    ["Resolve routine partner follow-ups", "Maintain listing completeness and consistency", "Surface blockers to vendor leads quickly"],
    [
      { title: "Catalog visibility", body: "Inspect storefront-facing inventory and category organization.", href: "/search", hrefLabel: "Browse catalog" },
      { title: "Staff focus", body: "Use this landing page as the distinct home for vendor staff operations." },
      { title: "Execution posture", body: "Keep routine partner work separate from vendor-lead planning and internal operations." }
    ]
  ),
  pharmacist: makeConfig(
    "pharmacist",
    "Pharmacist Dashboard",
    "Pharmacist dashboard",
    "Review prescription uploads, protect clinical safety, and move high-priority approvals with clear audit context.",
    [
      { label: "Primary surface", value: "Review queue", meta: "Prescription submissions and follow-up decisions" },
      { label: "Main objective", value: "Clinical safety", meta: "Approve, reject, or request clarification quickly" },
      { label: "Shared inputs", value: "Uploads + decisions", meta: "Every case should move toward a safe fulfillment outcome" }
    ],
    ["Prioritize urgent prescription reviews", "Resolve clarification-required cases", "Keep turnaround times predictable for customers"],
    [
      { title: "Prescription queue", body: "Open the active queue and start reviewing pending cases.", href: "/pharmacist/prescriptions", hrefLabel: "Open queue" },
      { title: "Customer context", body: "Understand what customers see while prescriptions move through review.", href: "/account/prescriptions", hrefLabel: "See customer view" },
      { title: "Safety posture", body: "Use this dashboard as the pharmacist-specific landing page before opening individual reviews." }
    ]
  ),
  doctor: makeConfig(
    "doctor",
    "Doctor Dashboard",
    "Doctor dashboard",
    "A clinician-facing landing page for prescription context, clarifications, and treatment communication touchpoints.",
    [
      { label: "Primary surface", value: "Clinical oversight", meta: "Prescription intent and therapy continuity" },
      { label: "Main objective", value: "Clarity", meta: "Reduce ambiguity that slows down pharmacist review" },
      { label: "Shared inputs", value: "Prescriptions + notes", meta: "Support safe dispensing decisions" }
    ],
    ["Support therapy clarification workflows", "Reduce avoidable review delays", "Provide clean prescribing context when needed"],
    [
      { title: "Prescription process", body: "See how uploads and reviews are represented in the customer experience.", href: "/upload-prescription", hrefLabel: "Open upload flow" },
      { title: "Clinical focus", body: "This dashboard marks a dedicated doctor landing experience separate from other employees." },
      { title: "Care coordination", body: "Use this landing page for prescribing context and clarification-oriented workflows." }
    ]
  ),
  warehouse_operator: makeConfig(
    "warehouse_operator",
    "Warehouse Dashboard",
    "Warehouse dashboard",
    "Run packing, dispatch readiness, and stock exception handling from an operations-first warehouse landing page.",
    [
      { label: "Primary surface", value: "Fulfillment", meta: "Packing, inventory posture, and dispatch coordination" },
      { label: "Main objective", value: "Shipment readiness", meta: "Move confirmed orders through physical fulfillment" },
      { label: "Shared inputs", value: "Orders + inventory", meta: "Stay aligned with delivery and catalog teams" }
    ],
    ["Work queued and packed orders in priority order", "Watch inventory gaps that block fulfillment", "Hand off dispatch-ready shipments cleanly"],
    [
      { title: "Order operations", body: "Work the live order pipeline and fulfillment statuses.", href: "/admin/orders", hrefLabel: "Open orders" },
      { title: "Inventory controls", body: "Inspect stock posture and product availability exceptions.", href: "/admin/inventory", hrefLabel: "Open inventory" },
      { title: "Delivery handoff", body: "Check dispatch readiness and downstream shipment state.", href: "/admin/delivery", hrefLabel: "Open delivery" }
    ]
  ),
  delivery_agent: makeConfig(
    "delivery_agent",
    "Delivery Dashboard",
    "Delivery dashboard",
    "A field-focused landing page for assigned drops, reattempt risk, and final-mile communication readiness.",
    [
      { label: "Primary surface", value: "Final mile", meta: "Delivery progress and completion handoff" },
      { label: "Main objective", value: "Successful delivery", meta: "Reduce failed attempts and improve ETA confidence" },
      { label: "Shared inputs", value: "Shipments + notes", meta: "Coordinate closely with warehouse and support teams" }
    ],
    ["Prioritize out-for-delivery work", "Capture blockers that need customer communication", "Escalate failed attempts and returns fast"],
    [
      { title: "Field focus", body: "This dashboard separates delivery work from warehouse and support landings." },
      { title: "Exception handling", body: "Track failed attempts, address issues, and reattempt-sensitive deliveries from a delivery-first perspective." },
      { title: "Storefront context", body: "Review customer-facing expectations around delivery and order completion.", href: "/account/orders", hrefLabel: "See order journey" }
    ]
  ),
  procurement_manager: makeConfig(
    "procurement_manager",
    "Procurement Dashboard",
    "Procurement dashboard",
    "A sourcing-oriented landing page for replenishment priorities, supplier follow-up, and stock risk reduction.",
    [
      { label: "Primary surface", value: "Replenishment", meta: "Procurement planning and supply continuity" },
      { label: "Main objective", value: "Availability", meta: "Prevent low-stock and out-of-stock interruptions" },
      { label: "Shared inputs", value: "Inventory + vendor signals", meta: "Feed operations with dependable restocking decisions" }
    ],
    ["Review low-stock and out-of-stock signals", "Coordinate replenishment with vendor partners", "Prioritize supply actions that unblock fulfillment"],
    [
      { title: "Planning focus", body: "This dashboard acts as the procurement-specific landing experience." },
      { title: "Availability posture", body: "Monitor replenishment priorities that protect search and checkout continuity." },
      { title: "Catalog visibility", body: "Cross-check customer-visible assortment and category breadth.", href: "/search", hrefLabel: "Browse catalog" }
    ]
  ),
  operations_manager: makeConfig(
    "operations_manager",
    "Operations Dashboard",
    "Operations dashboard",
    "A cross-functional operations landing page for order flow, dispatch health, and service-level risk monitoring.",
    [
      { label: "Primary surface", value: "Operations control", meta: "End-to-end order and fulfillment visibility" },
      { label: "Main objective", value: "Flow efficiency", meta: "Spot blockers before they hit customers" },
      { label: "Shared inputs", value: "Orders + delivery + stock", meta: "Coordinate multiple teams from one operating picture" }
    ],
    ["Watch backlog and throughput across key operational queues", "Balance stock, fulfillment, and dispatch priorities", "Escalate SLA risk before service levels slip"],
    [
      { title: "Cross-team focus", body: "Use this landing page to coordinate handoffs across warehouse, dispatch, procurement, and support." },
      { title: "Operational bottlenecks", body: "Track how stock, queue pressure, and delivery exceptions interact." },
      { title: "Customer-facing context", body: "Review the storefront and account journey when pressure-testing operations.", href: "/search", hrefLabel: "Open storefront" }
    ]
  ),
  support_agent: makeConfig(
    "support_agent",
    "Support Dashboard",
    "Support dashboard",
    "A customer-support landing page tuned for status lookups, payment troubleshooting, and fast order triage.",
    [
      { label: "Primary surface", value: "Case resolution", meta: "Status lookup and customer-facing issue handling" },
      { label: "Main objective", value: "Fast answers", meta: "Resolve customer blockers without bouncing between tools" },
      { label: "Shared inputs", value: "Orders + payments", meta: "Coordinate with warehouse, finance, and pharmacists as needed" }
    ],
    ["Handle order and payment inquiries quickly", "Triage delivery exceptions before they escalate", "Use access-friendly admin tools for customer support workflows"],
    [
      { title: "Orders", body: "Find and inspect customer orders during support calls.", href: "/admin/orders", hrefLabel: "Open orders" },
      { title: "Payments", body: "Review payment attempts and transaction exceptions.", href: "/admin/payments", hrefLabel: "Open payments" },
      { title: "Role directory", body: "Confirm which team should own escalated issues.", href: "/admin/roles", hrefLabel: "Open roles" }
    ]
  ),
  finance: makeConfig(
    "finance",
    "Finance Dashboard",
    "Finance dashboard",
    "A finance-first landing page for collections, reconciliation, settlements, and payment exception tracking.",
    [
      { label: "Primary surface", value: "Cash operations", meta: "Collections, reconciliation, and payout oversight" },
      { label: "Main objective", value: "Accuracy", meta: "Keep payment and settlement state trustworthy" },
      { label: "Shared inputs", value: "Payments + refunds", meta: "Stay synced with order and support activity" }
    ],
    ["Review collection and payment status", "Monitor reconciliation gaps and disputes", "Track settlements and refund-sensitive cases"],
    [
      { title: "Payments", body: "Inspect payment attempts and current transaction health.", href: "/admin/payments", hrefLabel: "Open payments" },
      { title: "Reconciliation", body: "Review mismatches and follow-up actions.", href: "/admin/reconciliation", hrefLabel: "Open reconciliation" },
      { title: "Settlements", body: "Monitor batch payouts and settlement drill-down.", href: "/admin/settlements", hrefLabel: "Open settlements" }
    ]
  ),
  catalog_manager: makeConfig(
    "catalog_manager",
    "Catalog Dashboard",
    "Catalog dashboard",
    "A catalog-led landing page for assortment quality, stock posture, and publish readiness.",
    [
      { label: "Primary surface", value: "Catalog control", meta: "Live products, publish state, and assortment consistency" },
      { label: "Main objective", value: "Discoverability", meta: "Keep products searchable, available, and cleanly merchandised" },
      { label: "Shared inputs", value: "Products + stock", meta: "Coordinate with procurement and support when items drift" }
    ],
    ["Maintain accurate live product listings", "Review stock-linked assortment gaps", "Prepare items for browse and search experiences"],
    [
      { title: "Products", body: "Create and update live catalog rows.", href: "/admin/products", hrefLabel: "Open products" },
      { title: "Inventory", body: "Check availability posture and stock-driven publishing issues.", href: "/admin/inventory", hrefLabel: "Open inventory" },
      { title: "Storefront search", body: "Inspect customer-facing catalog visibility.", href: "/search", hrefLabel: "Search catalog" }
    ]
  ),
  marketing_manager: makeConfig(
    "marketing_manager",
    "Marketing Dashboard",
    "Marketing dashboard",
    "A marketing-focused landing page for assortment visibility, campaign context, and merchandising health.",
    [
      { label: "Primary surface", value: "Merchandising", meta: "Campaign readiness and customer-facing presentation" },
      { label: "Main objective", value: "Visibility", meta: "Support discovery and conversion across the storefront" },
      { label: "Shared inputs", value: "Catalog + offers", meta: "Align campaigns with live product and category coverage" }
    ],
    ["Review high-visibility categories and assortment quality", "Coordinate campaigns with live product availability", "Track storefront readiness before promotions go live"],
    [
      { title: "Storefront", body: "Check the browse and search experience customers actually see.", href: "/search", hrefLabel: "Open storefront" },
      { title: "Marketing focus", body: "This dashboard establishes a dedicated marketing landing experience separate from catalog management." },
      { title: "Merchandising posture", body: "Use this landing page to align campaigns with assortment visibility and browse quality." }
    ]
  ),
  admin: makeConfig(
    "admin",
    "Admin Dashboard",
    "Admin dashboard",
    "A full back-office landing page for operational oversight, user access, and cross-functional execution.",
    [
      { label: "Primary surface", value: "Admin console", meta: "Broad operational visibility across workflows" },
      { label: "Main objective", value: "Control", meta: "Keep the platform moving and unblock teams quickly" },
      { label: "Shared inputs", value: "Orders + users + stock", meta: "Coordinate across support, catalog, finance, and fulfillment" }
    ],
    ["Watch platform-wide operational health", "Coordinate across multiple admin-facing modules", "Manage escalations, access, and execution priorities"],
    [
      { title: "Orders", body: "Open the central order operations surface.", href: "/admin/orders", hrefLabel: "Open orders" },
      { title: "Roles", body: "Review assigned working roles and access structure.", href: "/admin/roles", hrefLabel: "Open roles" },
      { title: "Products", body: "Jump into live catalog controls when needed.", href: "/admin/products", hrefLabel: "Open products" }
    ]
  ),
  compliance_officer: makeConfig(
    "compliance_officer",
    "Compliance Dashboard",
    "Compliance dashboard",
    "A governance-focused landing page for policy adherence, approval-sensitive workflows, and regulated process checks.",
    [
      { label: "Primary surface", value: "Compliance oversight", meta: "Sensitive workflow and control visibility" },
      { label: "Main objective", value: "Policy adherence", meta: "Reduce gaps across regulated activities" },
      { label: "Shared inputs", value: "Prescriptions + access + logs", meta: "Coordinate with pharmacists, admin, and auditors" }
    ],
    ["Watch for approval-sensitive exceptions", "Support traceable and policy-aligned operational decisions", "Keep regulated processes reviewable and consistent"],
    [
      { title: "Prescription context", body: "Understand clinically sensitive customer flows.", href: "/upload-prescription", hrefLabel: "Open prescription flow" },
      { title: "Governance focus", body: "This dashboard gives compliance its own landing experience instead of sharing a generic admin home." },
      { title: "Control boundaries", body: "Use this landing page to frame policy-sensitive review separately from everyday operations." }
    ]
  ),
  auditor: makeConfig(
    "auditor",
    "Auditor Dashboard",
    "Auditor dashboard",
    "An audit-ready landing page for control review, access tracing, and process verification across core workflows.",
    [
      { label: "Primary surface", value: "Audit review", meta: "Control evidence and process consistency" },
      { label: "Main objective", value: "Traceability", meta: "Verify who did what and where risk concentrates" },
      { label: "Shared inputs", value: "Access + workflow context", meta: "Support internal review without owning day-to-day operations" }
    ],
    ["Review separation of duties and control boundaries", "Inspect workflow coverage across operational roles", "Prepare for evidence-led checks and follow-ups"],
    [
      { title: "Audit focus", body: "This landing page keeps audit work distinct from finance, compliance, and admin dashboards." },
      { title: "Evidence posture", body: "Use this page to begin reviews with control context rather than operational execution tooling." },
      { title: "Customer journey reference", body: "Inspect customer-facing flows when validating process completeness.", href: "/account", hrefLabel: "Open account view" }
    ]
  ),
  viewer: makeConfig(
    "viewer",
    "Viewer Dashboard",
    "Viewer dashboard",
    "A read-oriented landing page for observers who need awareness without broad operational control.",
    [
      { label: "Primary surface", value: "Read-only visibility", meta: "Context without heavy write responsibility" },
      { label: "Main objective", value: "Awareness", meta: "Stay informed on process posture and role boundaries" },
      { label: "Shared inputs", value: "Summaries + access maps", meta: "Support executives, reviewers, and stakeholders" }
    ],
    ["Use dashboards to build situational awareness", "Review role boundaries before escalating questions", "Observe workflows without owning execution queues"],
    [
      { title: "Customer experience", body: "Review the storefront and account journey from a read-only perspective.", href: "/search", hrefLabel: "Open storefront" },
      { title: "Observer focus", body: "This dashboard makes viewer access feel deliberate rather than inherited from another role." },
      { title: "Situational awareness", body: "Use this landing page to stay informed without inheriting another team’s execution space." }
    ]
  ),
  security_admin: makeConfig(
    "security_admin",
    "Security Dashboard",
    "Security dashboard",
    "A security-first landing page for privileged access review, hardening posture, and sensitive workflow oversight.",
    [
      { label: "Primary surface", value: "Security oversight", meta: "Privileged access, role boundaries, and control review" },
      { label: "Main objective", value: "Risk reduction", meta: "Keep access posture deliberate and observable" },
      { label: "Shared inputs", value: "Roles + admin context", meta: "Coordinate with super admins and compliance stakeholders" }
    ],
    ["Review privileged role boundaries", "Watch for access patterns that need escalation", "Support safe administration of sensitive workflows"],
    [
      { title: "Security focus", body: "This dashboard establishes a separate security landing rather than inheriting the admin home." },
      { title: "Privileged access posture", body: "Review role boundaries and elevated access expectations from a security-first lens." },
      { title: "Customer-surface reference", body: "Inspect what the public-facing experience exposes while evaluating security posture.", href: "/search", hrefLabel: "Open storefront" }
    ]
  ),
  super_admin: makeConfig(
    "super_admin",
    "Super Admin Dashboard",
    "Super admin dashboard",
    "The highest-privilege landing page for platform-wide control, role governance, and cross-workspace oversight.",
    [
      { label: "Primary surface", value: "Platform control", meta: "Privileged access across operational and governance workflows" },
      { label: "Main objective", value: "Global oversight", meta: "See cross-functional health and manage elevated access concerns" },
      { label: "Shared inputs", value: "Roles + operations", meta: "Coordinate with admin, security, compliance, and finance stakeholders" }
    ],
    ["Review access boundaries and high-risk responsibilities", "Keep visibility across operations, finance, and regulated flows", "Use role-specific dashboards as distinct landing experiences by persona"],
    [
      { title: "Platform control", body: "Use this landing page as the top-level starting point for elevated platform work." },
      { title: "Cross-workspace review", body: "Move between customer, pharmacist, and role-specific dashboards when verifying global posture." },
      { title: "Storefront reference", body: "Keep a customer-facing view nearby while reviewing platform-wide changes.", href: "/search", hrefLabel: "Open storefront" }
    ]
  )
};

export function getRoleDashboardConfig(role: string | null | undefined) {
  if (!role) {
    return null;
  }

  return roleDashboardConfigs[role] ?? null;
}

export function getDashboardPathForRole(role: string | null | undefined) {
  if (!role) {
    return "/account";
  }

  if (role === "customer") {
    return "/account";
  }

  if (role === "pharmacist") {
    return "/pharmacist";
  }

  if (role === "admin" || role === "catalog_manager" || role === "finance" || role === "support_agent" || role === "warehouse_operator") {
    return "/admin/dashboard";
  }

  return `/workspace/${role}`;
}
