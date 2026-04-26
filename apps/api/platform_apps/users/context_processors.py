from .access import DASHBOARD_CONTENT, resolve_dashboard_url
from .views import PERMISSION_STATE_DENIED, resolve_role_permission_matrix_states


def portal_navigation(request):
    user = getattr(request, "user", None)
    role = getattr(user, "role", "") if getattr(user, "is_authenticated", False) else ""
    role_items = {
        "pharmacist": [
            {"label": "Review Queue", "url": "/pharmacist/dashboard/#queue", "icon": "clipboard2-pulse", "permission": "prescription_management.view"},
            {"label": "Approvals", "url": "/pharmacist/dashboard/#approvals", "icon": "shield-check", "permission": "prescription_management.approve"},
            {"label": "Alerts", "url": "/pharmacist/dashboard/#alerts", "icon": "bell", "permission": "prescription_management.view"},
        ],
        "vendor": [
            {"label": "Inventory", "url": "/vendor/dashboard/#inventory", "icon": "boxes", "permission": "inventory_warehouse.view_stock"},
            {"label": "Catalog", "url": "/vendor/dashboard/#catalog", "icon": "capsule", "permission": "medicine_catalog.view_medicines"},
            {"label": "Fulfillment", "url": "/vendor/dashboard/#fulfillment", "icon": "truck", "permission": "orders.view_orders"},
        ],
        "vendor_staff": [
            {"label": "Counter", "url": "/vendor-staff/dashboard/#counter", "icon": "shop", "permission": "orders.view_orders"},
            {"label": "Orders", "url": "/vendor-staff/dashboard/#orders", "icon": "bag-check", "permission": "orders.view_orders"},
            {"label": "Stock", "url": "/vendor-staff/dashboard/#stock", "icon": "boxes", "permission": "inventory_warehouse.view_stock"},
            {"label": "Catalog", "url": "/vendor-staff/dashboard/#catalog", "icon": "capsule-pill", "permission": "medicine_catalog.view_medicines"},
        ],
        "warehouse_operator": [
            {"label": "Stock Watch", "url": "/warehouse/dashboard/#stock-watch", "icon": "boxes", "permission": "inventory_warehouse.view_stock"},
            {"label": "Fulfillment", "url": "/warehouse/dashboard/#fulfillment", "icon": "box-seam", "permission": "orders.view_orders"},
            {"label": "Movements", "url": "/warehouse/dashboard/#movements", "icon": "arrow-left-right", "permission": "inventory_warehouse.view_stock"},
        ],
        "delivery_agent": [
            {"label": "Shipments", "url": "/delivery/dashboard/#shipments", "icon": "truck", "permission": "orders.view_orders"},
            {"label": "Exceptions", "url": "/delivery/dashboard/#exceptions", "icon": "exclamation-triangle", "permission": "orders.view_orders"},
            {"label": "Timeline", "url": "/delivery/dashboard/#timeline", "icon": "clock-history", "permission": "orders.view_orders"},
        ],
        "support_agent": [
            {"label": "Customer Signals", "url": "/support/dashboard/#customer-signals", "icon": "person-heart", "permission": "core_access.profile_others"},
            {"label": "Orders", "url": "/support/dashboard/#orders", "icon": "bag-check", "permission": "orders.view_orders"},
            {"label": "Prescriptions", "url": "/support/dashboard/#prescriptions", "icon": "file-earmark-medical", "permission": "prescription_management.view"},
        ],
        "finance": [
            {"label": "Revenue", "url": "/finance/dashboard/#revenue", "icon": "currency-rupee", "permission": "finance.view_transactions"},
            {"label": "Refunds", "url": "/finance/dashboard/#refunds", "icon": "arrow-counterclockwise", "permission": "finance.refund"},
            {"label": "Settlements", "url": "/finance/dashboard/#settlements", "icon": "receipt-cutoff", "permission": "finance.payouts"},
        ],
        "security_admin": [
            {"label": "Login Risk", "url": "/security/dashboard/#login-risk", "icon": "shield-exclamation", "permission": "security_audit.view_logs"},
            {"label": "Account Controls", "url": "/security/dashboard/#account-controls", "icon": "person-lock", "permission": "security_audit.block_users"},
            {"label": "Audit Watch", "url": "/security/dashboard/#audit-watch", "icon": "journal-lock", "permission": "security_audit.audit_data"},
        ],
        "doctor": [
            {"label": "Clinical Queue", "url": "/doctor/dashboard/#clinical-queue", "icon": "clipboard2-pulse", "permission": "prescription_management.view"},
            {"label": "Doctor Activity", "url": "/doctor/dashboard/#doctor-activity", "icon": "person-vcard", "permission": "prescription_management.view"},
            {"label": "Recent Cases", "url": "/doctor/dashboard/#recent-cases", "icon": "file-earmark-medical", "permission": "prescription_management.view"},
        ],
        "operations_manager": [
            {"label": "Approvals", "url": "/operations/dashboard/#approvals", "icon": "clipboard-check", "permission": "prescription_management.approve"},
            {"label": "Orders", "url": "/operations/dashboard/#orders", "icon": "bag-check", "permission": "orders.view_orders"},
            {"label": "Fulfillment", "url": "/operations/dashboard/#fulfillment", "icon": "truck", "permission": "inventory_warehouse.view_stock"},
        ],
        "catalog_manager": [
            {"label": "Coverage", "url": "/catalog/dashboard/#coverage", "icon": "capsule-pill", "permission": "medicine_catalog.view_medicines"},
            {"label": "Structure", "url": "/catalog/dashboard/#structure", "icon": "diagram-3", "permission": "medicine_catalog.edit_medicine"},
            {"label": "Substitutes", "url": "/catalog/dashboard/#substitutes", "icon": "shuffle", "permission": "medicine_catalog.edit_medicine"},
        ],
        "procurement_manager": [
            {"label": "Replenishment", "url": "/procurement/dashboard/#replenishment", "icon": "cart-plus", "permission": "inventory_warehouse.view_stock"},
            {"label": "Inbound", "url": "/procurement/dashboard/#inbound", "icon": "box-arrow-in-down", "permission": "inventory_warehouse.receive_stock"},
            {"label": "Restocks", "url": "/procurement/dashboard/#restocks", "icon": "arrow-repeat", "permission": "inventory_warehouse.add_stock"},
        ],
        "marketing_manager": [
            {"label": "Audience", "url": "/marketing/dashboard/#audience", "icon": "people", "permission": "reports.view_reports"},
            {"label": "Demand", "url": "/marketing/dashboard/#demand", "icon": "graph-up-arrow", "permission": "reports.view_reports"},
            {"label": "Catalog Focus", "url": "/marketing/dashboard/#catalog-focus", "icon": "megaphone", "permission": "medicine_catalog.view_medicines"},
        ],
        "compliance_officer": [
            {"label": "Audit Watch", "url": "/compliance/dashboard/#audit-watch", "icon": "journal-check", "permission": "security_audit.audit_data"},
            {"label": "Approvals", "url": "/compliance/dashboard/#approval-exceptions", "icon": "clipboard-x", "permission": "security_audit.audit_data"},
            {"label": "Clinical Risk", "url": "/compliance/dashboard/#clinical-risk", "icon": "shield-exclamation", "permission": "prescription_management.view"},
        ],
        "auditor": [
            {"label": "Evidence", "url": "/auditor/dashboard/#evidence", "icon": "journal-text", "permission": "security_audit.audit_data"},
            {"label": "Operational Trace", "url": "/auditor/dashboard/#operations-trace", "icon": "activity", "permission": "reports.view_reports"},
            {"label": "Approval Trail", "url": "/auditor/dashboard/#approval-trail", "icon": "clipboard-data", "permission": "reports.view_reports"},
        ],
        "viewer": [
            {"label": "Overview", "url": "/viewer/dashboard/#overview", "icon": "grid", "permission": "reports.view_reports"},
            {"label": "Orders", "url": "/viewer/dashboard/#orders", "icon": "bag-check", "permission": "orders.view_orders"},
            {"label": "Prescriptions", "url": "/viewer/dashboard/#prescriptions", "icon": "file-earmark-medical", "permission": "prescription_management.view"},
            {"label": "Alerts", "url": "/viewer/dashboard/#alerts", "icon": "bell", "permission": "security_audit.view_logs"},
        ],
        "admin": [
            {"label": "Operations", "url": "/admin/dashboard/#operations", "icon": "activity", "permission": "orders.view_orders"},
            {"label": "Approvals", "url": "/admin/dashboard/#approvals", "icon": "clipboard-check", "permission": "prescription_management.approve"},
            {"label": "Users", "url": "/admin/dashboard/#users", "icon": "people", "permission": "user_management.view_users"},
            {"label": "Audit", "url": "/admin/dashboard/#audit", "icon": "journal-text", "permission": "security_audit.view_logs"},
        ],
        "super_admin": [
            {"label": "Security", "url": "/super-admin/dashboard/#security", "icon": "shield-lock", "permission": "security_audit.security_control"},
            {"label": "Platform", "url": "/super-admin/dashboard/#platform", "icon": "diagram-3", "permission": "settings.platform_settings"},
            {"label": "Approvals", "url": "/super-admin/dashboard/#approvals", "icon": "clipboard-check", "permission": "prescription_management.approve"},
            {"label": "Operations", "url": "/super-admin/dashboard/#operations", "icon": "activity", "permission": "orders.view_orders"},
            {"label": "Staff", "url": "/super-admin/dashboard/#staff", "icon": "people", "permission": "user_management.view_users"},
            {"label": "Privileges", "url": "/super-admin/dashboard/#privileges", "icon": "key", "permission": "security_audit.security_control"},
            {"label": "Audit", "url": "/super-admin/dashboard/#audit", "icon": "journal-text", "permission": "security_audit.audit_data"},
            {"label": "Health", "url": "/super-admin/dashboard/#health", "icon": "heart-pulse", "permission": "reports.view_reports"},
        ],
    }
    dashboard_item = {"label": "Dashboard", "url": resolve_dashboard_url(user), "icon": "grid", "permission": "core_access.dashboard_access"}
    profile_item = {"label": "Profile API", "url": "/api/v1/auth/me/", "icon": "person", "permission": "core_access.profile_own"}
    sidebar_items = [dashboard_item] + role_items.get(role, []) + [profile_item]
    role_states = resolve_role_permission_matrix_states(role) if role else {}
    filtered_sidebar = [
        {key: value for key, value in item.items() if key != "permission"}
        for item in sidebar_items
        if not item.get("permission")
        or getattr(user, "is_superuser", False)
        or role_states.get(item["permission"], PERMISSION_STATE_DENIED) != PERMISSION_STATE_DENIED
    ]
    return {
        "role_sidebar": filtered_sidebar if role in DASHBOARD_CONTENT else [],
        "portal_role_config": DASHBOARD_CONTENT.get(role, {}),
    }
