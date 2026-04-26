from __future__ import annotations

from .models import User


ENTERPRISE_ROLE_CATALOG = (
    {
        "role_value": "customer",
        "role": "Customer",
        "type_of_user_value": "customer",
        "type_of_user": "Customer",
        "category": "End User",
        "department": "End User",
        "designation": "Customer",
    },
    {
        "role_value": "vendor",
        "role": "Vendor",
        "type_of_user_value": "partner",
        "type_of_user": "Partner",
        "category": "Business",
        "department": "Business / Partners",
        "designation": "Store Owner / Vendor",
    },
    {
        "role_value": "vendor_staff",
        "role": "Vendor Staff",
        "type_of_user_value": "partner",
        "type_of_user": "Partner",
        "category": "Business",
        "department": "Business / Partners",
        "designation": "Store Staff / Sales Executive",
    },
    {
        "role_value": "pharmacist",
        "role": "Pharmacist",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Healthcare",
        "department": "Healthcare",
        "designation": "Licensed Pharmacist",
    },
    {
        "role_value": "doctor",
        "role": "Doctor",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Healthcare",
        "department": "Healthcare",
        "designation": "Medical Doctor / Physician",
    },
    {
        "role_value": "warehouse_operator",
        "role": "Warehouse Operator",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Operations",
        "department": "Operations",
        "designation": "Warehouse Executive",
    },
    {
        "role_value": "delivery_agent",
        "role": "Delivery Agent",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Operations",
        "department": "Logistics",
        "designation": "Delivery Executive",
    },
    {
        "role_value": "procurement_manager",
        "role": "Procurement Manager",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Operations",
        "department": "Operations",
        "designation": "Procurement Manager",
    },
    {
        "role_value": "operations_manager",
        "role": "Operations Manager",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Operations",
        "department": "Operations",
        "designation": "Operations Manager",
    },
    {
        "role_value": "support_agent",
        "role": "Support Agent",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Support",
        "department": "Customer Support",
        "designation": "Support Executive",
    },
    {
        "role_value": "finance",
        "role": "Finance",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Finance",
        "department": "Finance",
        "designation": "Finance Executive / Accounts Officer",
    },
    {
        "role_value": "catalog_manager",
        "role": "Catalog Manager",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Management",
        "department": "Product Management",
        "designation": "Catalog Manager / Product Manager",
    },
    {
        "role_value": "marketing_manager",
        "role": "Marketing Manager",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Management",
        "department": "Marketing",
        "designation": "Marketing Manager / Growth Manager",
    },
    {
        "role_value": "admin",
        "role": "Admin",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Management",
        "department": "Administration",
        "designation": "System Administrator / Platform Admin",
    },
    {
        "role_value": "compliance_officer",
        "role": "Compliance Officer",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Compliance",
        "department": "Compliance",
        "designation": "Compliance Officer",
    },
    {
        "role_value": "auditor",
        "role": "Auditor",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "Compliance",
        "department": "Compliance",
        "designation": "Internal Auditor",
    },
    {
        "role_value": "viewer",
        "role": "Viewer",
        "type_of_user_value": "employee",
        "type_of_user": "Employee",
        "category": "General",
        "department": "General / Reporting",
        "designation": "Analyst / Viewer",
    },
    {
        "role_value": "security_admin",
        "role": "Security Admin",
        "type_of_user_value": "system",
        "type_of_user": "System",
        "category": "Security",
        "department": "IT Security",
        "designation": "Security Administrator",
    },
    {
        "role_value": "super_admin",
        "role": "Super Admin",
        "type_of_user_value": "system",
        "type_of_user": "System",
        "category": "Core System",
        "department": "Executive / System",
        "designation": "Super Administrator / System Owner",
    },
)

ENTERPRISE_ROLE_CATALOG_BY_ROLE = {entry["role_value"]: entry for entry in ENTERPRISE_ROLE_CATALOG}


def get_role_catalog_entry(role_value: str) -> dict | None:
    return ENTERPRISE_ROLE_CATALOG_BY_ROLE.get((role_value or "").strip())


def get_role_catalog_payload() -> list[dict]:
    payload: list[dict] = []
    type_labels = dict(User.TYPE_OF_USER_CHOICES)
    for entry in ENTERPRISE_ROLE_CATALOG:
        payload.append(
            {
                **entry,
                "type_of_user_label": type_labels.get(entry["type_of_user_value"], entry["type_of_user"]),
            }
        )
    return payload
