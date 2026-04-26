import csv

from django.contrib import admin
from django.contrib import messages
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.http import FileResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import include, path
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from datetime import timedelta

from platform_apps.users.web_views import access_denied_view

handler403 = access_denied_view

admin.site.site_header = "TrueCare Backoffice"
admin.site.site_title = "TrueCare Admin"
admin.site.index_title = "Operations and catalog control center"


def api_root(_request):
    return JsonResponse(
        {
            "service": "rakeshmed-api",
            "version": "v1",
            "status": "ok",
            "docs_hint": "Use /api/v1/health/live/ or /api/v1/health/ready/",
            "deprecation_policy": "Additive changes may ship within v1; breaking changes require a new versioned path.",
            "compliance": {
                "company_name": settings.COMPLIANCE_COMPANY_NAME,
                "support_email": settings.COMPLIANCE_SUPPORT_EMAIL,
                "grievance_email": settings.COMPLIANCE_GRIEVANCE_EMAIL,
                "grievance_officer": settings.COMPLIANCE_GRIEVANCE_OFFICER,
                "drug_license_number": settings.COMPLIANCE_DRUG_LICENSE_NUMBER,
                "drug_license_authority": settings.COMPLIANCE_DRUG_LICENSE_AUTHORITY,
                "pharmacist_in_charge": settings.COMPLIANCE_PHARMACIST_IN_CHARGE,
                "pharmacist_registration_number": settings.COMPLIANCE_PHARMACIST_REGISTRATION_NUMBER,
            },
        }
    )


def _dashboard_context(request):
    from platform_apps.audit.models import AuditLog, ManagedFile
    from platform_apps.catalog.models import Category, Product
    from platform_apps.inventory.services import inventory_risk_snapshot
    from platform_apps.notifications.models import Notification
    from platform_apps.orders.models import Order, PaymentAttempt
    from platform_apps.prescriptions.models import Prescription
    from platform_apps.users.models import User

    recent_orders = list(Order.objects.select_related("user").order_by("-created_at")[:5])
    recent_prescriptions = list(Prescription.objects.select_related("user", "reviewed_by").order_by("-created_at")[:5])
    recent_payments = list(PaymentAttempt.objects.select_related("order").order_by("-initiated_at")[:5])
    recent_audit_logs = list(AuditLog.objects.select_related("actor").order_by("-created_at")[:6])
    recent_files = list(ManagedFile.objects.select_related("uploaded_by").order_by("-created_at")[:6])
    recent_notifications = list(Notification.objects.select_related("user").order_by("-created_at")[:5])
    inventory_risk = inventory_risk_snapshot()
    total_revenue = Order.objects.filter(payment_status="paid").aggregate(total=Sum("total")).get("total") or 0
    captured_payments = PaymentAttempt.objects.filter(status="captured").aggregate(total=Sum("amount")).get("total") or 0
    today = timezone.localdate()
    trend_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]

    order_trend = []
    prescription_trend = []
    revenue_trend = []
    paid_orders_trend = []
    for day in trend_days:
        orders_count = Order.objects.filter(created_at__date=day).count()
        prescriptions_count = Prescription.objects.filter(created_at__date=day).count()
        paid_total = Order.objects.filter(created_at__date=day, payment_status="paid").aggregate(total=Sum("total")).get("total") or 0
        paid_count = Order.objects.filter(created_at__date=day, payment_status="paid").count()

        order_trend.append({"label": day.strftime("%d %b"), "value": orders_count})
        prescription_trend.append({"label": day.strftime("%d %b"), "value": prescriptions_count})
        revenue_trend.append({"label": day.strftime("%d %b"), "value": float(paid_total)})
        paid_orders_trend.append({"label": day.strftime("%d %b"), "value": paid_count})

    def with_bars(items):
        max_value = max((item["value"] for item in items), default=0)
        for item in items:
            item["bar_height"] = 14 if max_value == 0 else max(14, round((item["value"] / max_value) * 100))
        return items

    order_status_breakdown = [
        {
            "label": "Placed",
            "value": Order.objects.filter(status="placed").count(),
            "href": f"{reverse('admin:orders_order_changelist')}?status__exact=placed",
        },
        {
            "label": "Pending Prescription Review",
            "value": Order.objects.filter(status="pending_prescription_review").count(),
            "href": f"{reverse('admin:orders_order_changelist')}?status__exact=pending_prescription_review",
        },
        {
            "label": "Confirmed",
            "value": Order.objects.filter(status="confirmed").count(),
            "href": f"{reverse('admin:orders_order_changelist')}?status__exact=confirmed",
        },
        {
            "label": "Cancelled",
            "value": Order.objects.filter(status="cancelled").count(),
            "href": f"{reverse('admin:orders_order_changelist')}?status__exact=cancelled",
        },
    ]
    prescription_status_breakdown = [
        {
            "label": "Submitted",
            "value": Prescription.objects.filter(status="submitted").count(),
            "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=submitted",
        },
        {
            "label": "Pending Review",
            "value": Prescription.objects.filter(status="pending_review").count(),
            "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review",
        },
        {
            "label": "Clarification Required",
            "value": Prescription.objects.filter(status="clarification_required").count(),
            "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=clarification_required",
        },
        {
            "label": "Approved",
            "value": Prescription.objects.filter(status="approved").count(),
            "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=approved",
        },
    ]

    user_role = getattr(request.user, "role", "admin")
    role_dashboard_map = {
        "pharmacist": {
            "eyebrow": "Pharmacist Console",
            "headline": "Review prescriptions, resolve clarifications, and keep medicine approvals moving.",
            "description": "Your homepage is optimized for prescription queues, urgent reviews, and recent uploads that need attention.",
            "chips": ["Pending reviews", "Urgent queue", "Clarifications"],
        },
        "catalog_manager": {
            "eyebrow": "Catalog Console",
            "headline": "Shape navigation, categories, products, and substitutes with less admin friction.",
            "description": "Your homepage is optimized for catalog coverage, category structure, and product management shortcuts.",
            "chips": ["Categories", "Products", "Stock coverage"],
        },
        "finance": {
            "eyebrow": "Finance Console",
            "headline": "Track paid revenue, captured payments, settlements, and payment quality in one place.",
            "description": "Your homepage is optimized for payment health, captured amounts, and settlement-oriented flows.",
            "chips": ["Revenue", "Payments", "Settlements"],
        },
        "warehouse_operator": {
            "eyebrow": "Operations Console",
            "headline": "Keep orders moving with a tighter view of placed, confirmed, and review-blocked work.",
            "description": "Your homepage is optimized for order throughput, blocked orders, and action-heavy task lists.",
            "chips": ["Placed orders", "Confirmed orders", "Blocked flow"],
        },
        "support_agent": {
            "eyebrow": "Support Console",
            "headline": "Understand customer, prescription, and order activity before every support response.",
            "description": "Your homepage is optimized for customer-facing issues, active orders, and fast navigation.",
            "chips": ["Customers", "Orders", "Prescription help"],
        },
        "viewer": {
            "eyebrow": "Viewer Console",
            "headline": "Monitor operations, system health, and live activity with a read-only mission view.",
            "description": "Your homepage is optimized for situational awareness, alerts, and timeline visibility without edit-heavy shortcuts.",
            "chips": ["Read only", "Health", "Audit trail"],
        },
        "admin": {
            "eyebrow": "TrueCare Operations",
            "headline": "Run catalog, customer care, and prescription workflows from one control center.",
            "description": "Keep the pharmacy storefront healthy, review prescription queues faster, and move from insight to action without digging through model lists.",
            "chips": ["Catalog", "Orders", "Prescriptions"],
        },
    }
    role_dashboard = role_dashboard_map.get(user_role, role_dashboard_map["admin"])

    role_focus_panels_map = {
        "pharmacist": [
            {
                "title": "Pharmacist Focus",
                "items": [
                    {
                        "label": "Pending review queue",
                        "value": Prescription.objects.filter(status="pending_review").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review",
                    },
                    {
                        "label": "Urgent review queue",
                        "value": Prescription.objects.filter(status="pending_review", review_priority="urgent").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review&review_priority__exact=urgent",
                    },
                    {
                        "label": "Clarification cases",
                        "value": Prescription.objects.filter(status="clarification_required").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=clarification_required",
                    },
                ],
            }
        ],
        "catalog_manager": [
            {
                "title": "Catalog Focus",
                "items": [
                    {
                        "label": "Active products",
                        "value": Product.objects.filter(is_active=True).count(),
                        "href": reverse("admin:catalog_product_changelist"),
                    },
                    {
                        "label": "In-stock products",
                        "value": Product.objects.filter(is_active=True, stock_status="in_stock").count(),
                        "href": f"{reverse('admin:catalog_product_changelist')}?stock_status__exact=in_stock",
                    },
                    {
                        "label": "Category nodes",
                        "value": Category.objects.filter(is_active=True).count(),
                        "href": reverse("admin:catalog_category_changelist"),
                    },
                ],
            }
        ],
        "finance": [
            {
                "title": "Finance Focus",
                "items": [
                    {
                        "label": "Paid revenue",
                        "value": f"{total_revenue:,.2f}",
                        "href": f"{reverse('admin:orders_order_changelist')}?payment_status__exact=paid",
                    },
                    {
                        "label": "Captured payments",
                        "value": f"{captured_payments:,.2f}",
                        "href": f"{reverse('admin:orders_paymentattempt_changelist')}?status__exact=captured",
                    },
                    {
                        "label": "Failed payments",
                        "value": PaymentAttempt.objects.filter(status="failed").count(),
                        "href": f"{reverse('admin:orders_paymentattempt_changelist')}?status__exact=failed",
                    },
                ],
            }
        ],
    }
    role_focus_panels = role_focus_panels_map.get(user_role, [])
    role_layout_map = {
        "pharmacist": {
            "show_business_tiles": False,
            "show_today_tiles": True,
            "show_role_shortcuts": False,
            "show_task_board": True,
            "show_status_mix": True,
            "show_trends": False,
            "show_recent_orders": False,
            "show_recent_prescriptions": True,
            "show_backend_modules": False,
        },
        "catalog_manager": {
            "show_business_tiles": True,
            "show_today_tiles": False,
            "show_role_shortcuts": False,
            "show_task_board": False,
            "show_status_mix": False,
            "show_trends": True,
            "show_recent_orders": False,
            "show_recent_prescriptions": False,
            "show_backend_modules": True,
        },
        "finance": {
            "show_business_tiles": True,
            "show_today_tiles": True,
            "show_role_shortcuts": False,
            "show_task_board": False,
            "show_status_mix": False,
            "show_trends": True,
            "show_recent_orders": True,
            "show_recent_prescriptions": False,
            "show_backend_modules": False,
        },
        "warehouse_operator": {
            "show_business_tiles": False,
            "show_today_tiles": True,
            "show_role_shortcuts": False,
            "show_task_board": True,
            "show_status_mix": True,
            "show_trends": True,
            "show_recent_orders": True,
            "show_recent_prescriptions": False,
            "show_backend_modules": False,
        },
        "support_agent": {
            "show_business_tiles": False,
            "show_today_tiles": True,
            "show_role_shortcuts": True,
            "show_task_board": False,
            "show_status_mix": True,
            "show_trends": False,
            "show_recent_orders": True,
            "show_recent_prescriptions": True,
            "show_backend_modules": False,
        },
        "viewer": {
            "show_business_tiles": True,
            "show_today_tiles": True,
            "show_role_shortcuts": False,
            "show_task_board": False,
            "show_status_mix": True,
            "show_trends": True,
            "show_recent_orders": True,
            "show_recent_prescriptions": True,
            "show_backend_modules": False,
        },
        "admin": {
            "show_business_tiles": True,
            "show_today_tiles": True,
            "show_role_shortcuts": True,
            "show_task_board": True,
            "show_status_mix": True,
            "show_trends": True,
            "show_recent_orders": True,
            "show_recent_prescriptions": True,
            "show_backend_modules": True,
        },
    }
    role_layout = role_layout_map.get(user_role, role_layout_map["admin"])
    role_app_visibility = {
        "pharmacist": {"Prescriptions", "Notifications", "Audit and Files"},
        "catalog_manager": {"Catalog", "Audit and Files"},
        "finance": {"Orders", "Notifications", "Audit and Files"},
        "warehouse_operator": {"Orders", "Prescriptions", "Audit and Files"},
        "support_agent": {"Users", "Orders", "Prescriptions", "Notifications", "Audit and Files"},
        "viewer": {"Audit and Files", "Notifications"},
        "admin": None,
    }

    active_products = Product.objects.filter(is_active=True).count()
    total_products = Product.objects.count() or 1
    open_orders = Order.objects.filter(status__in=["placed", "pending_prescription_review", "confirmed"]).count()
    pending_reviews = Prescription.objects.filter(status__in=["submitted", "pending_review", "clarification_required"]).count()
    failed_payments = PaymentAttempt.objects.filter(status="failed").count()
    unread_notifications = Notification.objects.filter(is_read=False).count()
    pending_approvals = User.objects.filter(approval_status="pending", role__in=["vendor", "pharmacist"]).count()
    overdue_approvals = User.objects.filter(
        approval_status="pending",
        role__in=["vendor", "pharmacist"],
        approval_due_at__isnull=False,
        approval_due_at__lt=timezone.now(),
    ).count()
    approval_queue_base_url = reverse("admin-approval-queue")
    pending_approval_users = list(
        User.objects.filter(approval_status="pending", role__in=["vendor", "pharmacist"]).order_by("created_at")[:6]
    )
    overdue_approval_users = list(
        User.objects.filter(
            approval_status="pending",
            role__in=["vendor", "pharmacist"],
            approval_due_at__isnull=False,
            approval_due_at__lt=timezone.now(),
        )
        .select_related("approval_assigned_to")
        .order_by("approval_due_at")[:6]
    )
    for user in overdue_approval_users:
        _apply_assignment_sla(user)
        user.approval_queue_href = _approval_queue_url(
            approval_queue_base_url,
            assigned_to=str(user.approval_assigned_to_id or ""),
            overdue_only=True,
        )
    for user in pending_approval_users:
        user.approval_queue_href = _approval_queue_url(
            approval_queue_base_url,
            assigned_to=str(user.approval_assigned_to_id or ""),
        )
    dashboard_approval_presets = _approval_queue_presets(request.user, approval_queue_base_url)
    approval_reviewer_workloads = _approval_reviewer_workload_rows(approval_queue_base_url)
    recent_approved_count = User.objects.filter(
        approval_status="approved",
        role__in=["vendor", "pharmacist"],
        approval_reviewed_at__gte=timezone.now() - timedelta(days=7),
    ).count()
    approval_preset_tiles = [
        {
            "label": "My Queue",
            "value": User.objects.filter(
                approval_status="pending",
                role__in=["vendor", "pharmacist"],
                approval_assigned_to=request.user,
            ).count(),
            "meta": "Approvals currently assigned to you",
            "href": _approval_queue_url(approval_queue_base_url, assigned_to=str(request.user.pk)),
        },
        {
            "label": "My Overdue",
            "value": User.objects.filter(
                approval_status="pending",
                role__in=["vendor", "pharmacist"],
                approval_assigned_to=request.user,
                approval_due_at__isnull=False,
                approval_due_at__lt=timezone.now(),
            ).count(),
            "meta": "Your approvals that crossed SLA",
            "href": _approval_queue_url(approval_queue_base_url, assigned_to=str(request.user.pk), overdue_only=True),
        },
        {
            "label": "Unassigned Approvals",
            "value": User.objects.filter(
                approval_status="pending",
                role__in=["vendor", "pharmacist"],
                approval_assigned_to__isnull=True,
            ).count(),
            "meta": "Requests still waiting for ownership",
            "href": _approval_queue_url(approval_queue_base_url, assigned_to="unassigned"),
        },
        {
            "label": "Document Rejected",
            "value": User.objects.filter(
                approval_status="pending",
                role__in=["vendor", "pharmacist"],
            )
            .filter(
                Q(role="vendor", vendor_license_document_status="rejected")
                | Q(role="pharmacist", pharmacist_registration_document_status="rejected")
            )
            .count(),
            "meta": "Pending requests blocked on proof rework",
            "href": _approval_queue_url(approval_queue_base_url, document_rejected_only=True),
        },
        {
            "label": "Recently Approved",
            "value": recent_approved_count,
            "meta": "Vendor and pharmacist approvals completed in the last 7 days",
            "href": f"{reverse('admin:users_user_changelist')}?approval_status__exact=approved",
        },
    ]
    overdue_approval_by_owner = []
    for row in (
        User.objects.filter(
            approval_status="pending",
            role__in=["vendor", "pharmacist"],
            approval_due_at__isnull=False,
            approval_due_at__lt=timezone.now(),
        )
        .values("approval_assigned_to", "approval_assigned_to__full_name", "approval_assigned_to__email", "approval_assigned_to__phone_number")
        .annotate(total=Count("id"))
        .order_by("-total", "approval_assigned_to__full_name", "approval_assigned_to__email")[:6]
    ):
        owner_label = (
            row["approval_assigned_to__full_name"]
            or row["approval_assigned_to__email"]
            or row["approval_assigned_to__phone_number"]
            or "Unassigned"
        )
        overdue_approval_by_owner.append(
            {
                "owner_label": owner_label,
                "count": row["total"],
                "href": _approval_queue_url(
                    approval_queue_base_url,
                    assigned_to=str(row["approval_assigned_to"] or ""),
                    overdue_only=True,
                ),
            }
        )
    recent_approval_escalations = [
        {
            "title": entry.message,
            "meta": f"{entry.actor_label or 'System'} | {timezone.localtime(entry.created_at).strftime('%d %b %I:%M %p')}",
            "href": _approval_queue_url(approval_queue_base_url, escalated_only=True),
        }
        for entry in AuditLog.objects.filter(event_type="approval_sla_escalated").order_by("-created_at")[:5]
    ]
    open_orders_base = max(open_orders + Order.objects.filter(status="cancelled").count(), 1)
    pending_reviews_base = max(Prescription.objects.count(), 1)
    payment_attempts_base = max(PaymentAttempt.objects.count(), 1)

    performance_rings = [
        {
            "label": "Catalog Coverage",
            "value": round((Product.objects.filter(is_active=True, stock_status="in_stock").count() / total_products) * 100),
            "meta": "In-stock active catalog",
        },
        {
            "label": "Order Throughput",
            "value": max(5, min(100, round((Order.objects.filter(status="confirmed").count() / open_orders_base) * 100))),
            "meta": "Confirmed vs active flow",
        },
        {
            "label": "Review SLA",
            "value": max(5, min(100, 100 - round((pending_reviews / pending_reviews_base) * 100))),
            "meta": "Pending review pressure",
        },
        {
            "label": "Payment Reliability",
            "value": max(5, min(100, 100 - round((failed_payments / payment_attempts_base) * 100))),
            "meta": "Failed attempt resistance",
        },
    ]

    system_health_panels = [
        {
            "label": "API Gateway",
            "status": "Online",
            "tone": "online",
            "meta": "Routing storefront and admin traffic",
        },
        {
            "label": "Database",
            "status": "Healthy",
            "tone": "online",
            "meta": f"{Category.objects.count()} category records synced",
        },
        {
            "label": "Prescription Queue",
            "status": "Monitor",
            "tone": "warning" if pending_reviews else "online",
            "meta": f"{pending_reviews} reviews awaiting action",
        },
        {
            "label": "Payments",
            "status": "Watch",
            "tone": "warning" if failed_payments else "online",
            "meta": f"{failed_payments} failed attempts in queue",
        },
        {
            "label": "Alerts",
            "status": "Raised" if unread_notifications else "Quiet",
            "tone": "warning" if unread_notifications else "online",
            "meta": f"{unread_notifications} unread operational notifications",
        },
        {
            "label": "Inventory Risk",
            "status": "Watch" if inventory_risk["low_stock_count"] or inventory_risk["out_of_stock_count"] else "Healthy",
            "tone": "warning" if inventory_risk["low_stock_count"] or inventory_risk["out_of_stock_count"] else "online",
            "meta": (
                f"{inventory_risk['low_stock_count']} low-stock and "
                f"{inventory_risk['out_of_stock_count']} out-of-stock products"
            ),
        },
    ]

    activity_feed = []
    for order in recent_orders[:3]:
        activity_feed.append(
            {
                "title": f"Order {order.order_number}",
                "meta": f"{order.get_status_display()} for {order.user}",
                "timestamp": timezone.localtime(order.created_at).strftime("%d %b %I:%M %p"),
                "sort_key": order.created_at,
                "href": reverse("admin:orders_order_change", args=[order.pk]),
                "tone": "cyan",
            }
        )
    for prescription in recent_prescriptions[:3]:
        activity_feed.append(
            {
                "title": f"Prescription {prescription.reference_code}",
                "meta": f"{prescription.get_status_display()} for {prescription.patient_name}",
                "timestamp": timezone.localtime(prescription.created_at).strftime("%d %b %I:%M %p"),
                "sort_key": prescription.created_at,
                "href": reverse("admin:prescriptions_prescription_change", args=[prescription.pk]),
                "tone": "pink",
            }
        )
    for payment in recent_payments[:2]:
        activity_feed.append(
            {
                "title": f"Payment {payment.status.title()}",
                "meta": f"{payment.amount} on order {payment.order.order_number if payment.order_id else 'N/A'}",
                "timestamp": timezone.localtime(payment.initiated_at).strftime("%d %b %I:%M %p"),
                "sort_key": payment.initiated_at,
                "href": reverse("admin:orders_paymentattempt_change", args=[payment.pk]),
                "tone": "green" if payment.status == "captured" else "purple",
            }
        )
    for entry in recent_audit_logs[:2]:
        activity_feed.append(
            {
                "title": entry.message,
                "meta": f"{entry.entity_type.replace('_', ' ').title()} | {entry.actor_label or 'System'}",
                "timestamp": timezone.localtime(entry.created_at).strftime("%d %b %I:%M %p"),
                "sort_key": entry.created_at,
                "href": reverse("admin:audit_auditlog_changelist"),
                "tone": "green" if entry.severity == "info" else "amber",
            }
        )
    activity_feed = sorted(activity_feed, key=lambda item: item["sort_key"], reverse=True)[:8]
    for item in activity_feed:
        item.pop("sort_key", None)

    action_cards = [
        {
            "title": "Add Product",
            "description": "Create a new medicine or OTC product with pricing, content, and availability.",
            "href": reverse("admin:catalog_product_add"),
            "tone": "primary",
        },
        {
            "title": "Review Prescriptions",
            "description": "Jump straight into the pharmacist review queue and clear pending decisions.",
            "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review",
            "tone": "accent",
        },
        {
            "title": "Manage Categories",
            "description": "Update navbar groups, categories, and subcategories with the guided dropdown flow.",
            "href": reverse("admin:catalog_category_changelist"),
            "tone": "secondary",
        },
        {
            "title": "Track Orders",
            "description": "Monitor live customer orders, payment states, and delivery details.",
            "href": reverse("admin:orders_order_changelist"),
            "tone": "secondary",
        },
        {
            "title": "Upload Ops File",
            "description": "Store reports, invoices, exports, and compliance documents.",
            "href": reverse("admin:audit_managedfile_add"),
            "tone": "primary",
        },
    ]
    if user_role in {"admin", "super_admin"} or getattr(request.user, "is_superuser", False):
        action_cards.insert(
            0,
            {
                "title": "Review Access Requests",
                "description": "Approve or reject pending pharmacist and vendor registrations.",
                "href": reverse("admin-approval-queue"),
                "tone": "accent",
            },
        )
        action_cards.insert(
            1,
            {
                "title": "Manage Reviewer Schedules",
                "description": "Update approval specialties, shifts, leave dates, and temporary availability.",
                "href": reverse("admin-reviewer-schedules"),
                "tone": "secondary",
            },
        )
    if user_role == "viewer":
        action_cards = [
            {
                "title": "Open Audit Timeline",
                "description": "Watch the latest back-office events in a read-only view.",
                "href": reverse("admin:audit_auditlog_changelist"),
                "tone": "secondary",
            },
            {
                "title": "Open File Manager",
                "description": "Browse exports, reports, and uploaded documents.",
                "href": reverse("admin:audit_managedfile_changelist"),
                "tone": "primary",
            },
        ]

    command_items = [{"label": card["title"], "href": card["href"], "group": "Actions"} for card in action_cards]
    app_list = admin.site.get_app_list(request)
    visible_apps = role_app_visibility.get(user_role)
    if visible_apps is not None:
        app_list = [app for app in app_list if app["name"] in visible_apps]
    for app in app_list:
        for model in app["models"]:
            if model.get("admin_url"):
                command_items.append(
                    {
                        "label": model["name"],
                        "href": model["admin_url"],
                        "group": app["name"],
                    }
                )
            if model.get("add_url"):
                command_items.append(
                    {
                        "label": f"Add {model['name']}",
                        "href": model["add_url"],
                        "group": app["name"],
                    }
                )

    return {
        **admin.site.each_context(request),
        "title": "Backoffice Dashboard",
        "subtitle": "Overview",
        "role_dashboard": role_dashboard,
        "role_layout": role_layout,
        "user_role": user_role,
        "kpi_tiles": [
            {
                "label": "Active Products",
                "value": active_products,
                "meta": "Live storefront catalog",
            },
            {
                "label": "Category Nodes",
                "value": Category.objects.filter(is_active=True).count(),
                "meta": "Navbar, categories, and subcategories",
            },
            {
                "label": "Pending Reviews",
                "value": pending_reviews,
                "meta": "Prescription queue needing action",
            },
            {
                "label": "Open Orders",
                "value": open_orders,
                "meta": "Orders still in motion",
            },
        ],
        "alert_tiles": [
            {
                "label": "Unread Alerts",
                "value": unread_notifications,
                "meta": "Toast and notification pressure",
            },
            {
                "label": "Pending Approvals",
                "value": pending_approvals,
                "meta": "Vendor and pharmacist accounts awaiting approval",
            },
            {
                "label": "Overdue Approvals",
                "value": overdue_approvals,
                "meta": "Pending approvals beyond SLA",
            },
            {
                "label": "Low Stock SKUs",
                "value": inventory_risk["low_stock_count"],
                "meta": "Products drifting toward replenishment threshold",
            },
            {
                "label": "Audit Events",
                "value": AuditLog.objects.filter(created_at__date=today).count(),
                "meta": "Timeline entries generated today",
            },
            {
                "label": "Managed Files",
                "value": ManagedFile.objects.count(),
                "meta": "Docs and exports in the file manager",
            },
            {
                "label": "Viewer Safe Mode",
                "value": "On" if user_role == "viewer" else "Off",
                "meta": "Read-only access posture",
            },
        ],
        "role_focus_panels": role_focus_panels,
        "business_tiles": [
            {
                "label": "Paid Revenue",
                "value": f"{total_revenue:,.2f}",
                "meta": "Confirmed paid orders",
            },
            {
                "label": "Captured Payments",
                "value": f"{captured_payments:,.2f}",
                "meta": "Successful payment attempts",
            },
            {
                "label": "Active Customers",
                "value": User.objects.filter(role="customer", is_active=True).count(),
                "meta": "Customers with active accounts",
            },
            {
                "label": "Catalog Coverage",
                "value": Product.objects.filter(is_active=True, stock_status="in_stock").count(),
                "meta": "Products currently in stock",
            },
        ],
        "notification_panels": [
            {
                "title": notification.title,
                "kind": notification.get_kind_display(),
                "body": notification.body,
                "timestamp": timezone.localtime(notification.created_at).strftime("%d %b %I:%M %p"),
                "is_read": notification.is_read,
            }
            for notification in recent_notifications
        ],
        "audit_timeline": [
            {
                "title": entry.message,
                "meta": f"{entry.event_type.replace('_', ' ').title()} | {entry.actor_label or 'System'}",
                "severity": entry.severity,
                "timestamp": timezone.localtime(entry.created_at).strftime("%d %b %I:%M %p"),
            }
            for entry in recent_audit_logs
        ],
        "managed_files": [
            {
                "title": item.title,
                "category": item.get_category_display(),
                "size": item.file_size_bytes,
                "downloads": item.download_count,
                "href": reverse("admin-managed-file-download", args=[item.pk]),
            }
            for item in recent_files
        ],
        "today_tiles": [
            {
                "label": "Orders Today",
                "value": Order.objects.filter(created_at__date=today).count(),
                "meta": "New orders created today",
            },
            {
                "label": "Prescriptions Today",
                "value": Prescription.objects.filter(created_at__date=today).count(),
                "meta": "Uploads received today",
            },
            {
                "label": "Paid Orders Today",
                "value": Order.objects.filter(created_at__date=today, payment_status="paid").count(),
                "meta": "Orders paid on today's flow",
            },
            {
                "label": "New Customers Today",
                "value": User.objects.filter(created_at__date=today, role="customer").count(),
                "meta": "Customer signups created today",
            },
        ],
        "action_cards": action_cards,
        "status_breakdown_panels": [
            {"title": "Order Status Mix", "items": order_status_breakdown},
            {"title": "Prescription Status Mix", "items": prescription_status_breakdown},
        ],
        "trend_panels": [
            {
                "title": "Orders Over Last 7 Days",
                "summary": sum(item["value"] for item in order_trend),
                "suffix": "orders",
                "items": with_bars(order_trend),
            },
            {
                "title": "Prescriptions Over Last 7 Days",
                "summary": sum(item["value"] for item in prescription_trend),
                "suffix": "uploads",
                "items": with_bars(prescription_trend),
            },
            {
                "title": "Paid Revenue Over Last 7 Days",
                "summary": f"{sum(item['value'] for item in revenue_trend):,.2f}",
                "suffix": "revenue",
                "items": with_bars(revenue_trend),
            },
            {
                "title": "Paid Orders Over Last 7 Days",
                "summary": sum(item["value"] for item in paid_orders_trend),
                "suffix": "paid orders",
                "items": with_bars(paid_orders_trend),
            },
        ],
        "today_task_groups": [
            {
                "title": "Pharmacist Priorities",
                "tasks": [
                    {
                        "label": "Pending prescription reviews",
                        "value": Prescription.objects.filter(status="pending_review").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review",
                    },
                    {
                        "label": "Urgent prescription reviews",
                        "value": Prescription.objects.filter(status="pending_review", review_priority="urgent").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review&review_priority__exact=urgent",
                    },
                    {
                        "label": "Clarification follow-ups",
                        "value": Prescription.objects.filter(status="clarification_required").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=clarification_required",
                    },
                ],
            },
            {
                "title": "Operations Priorities",
                "tasks": [
                    {
                        "label": "Orders pending prescription review",
                        "value": Order.objects.filter(status="pending_prescription_review").count(),
                        "href": f"{reverse('admin:orders_order_changelist')}?status__exact=pending_prescription_review",
                    },
                    {
                        "label": "Placed orders awaiting action",
                        "value": Order.objects.filter(status="placed").count(),
                        "href": f"{reverse('admin:orders_order_changelist')}?status__exact=placed",
                    },
                    {
                        "label": "Failed payment attempts",
                        "value": failed_payments,
                        "href": f"{reverse('admin:orders_paymentattempt_changelist')}?status__exact=failed",
                    },
                    {
                        "label": "Low stock products",
                        "value": inventory_risk["low_stock_count"] + inventory_risk["out_of_stock_count"],
                        "href": f"{reverse('admin:catalog_product_changelist')}?stock_status__exact=low_stock",
                    },
                ],
            },
        ],
        "role_cards": [
            {
                "title": "Catalog Manager",
                "description": "Maintain navbar structure, categories, products, and substitutes.",
                "links": [
                    {"label": "Categories", "href": reverse("admin:catalog_category_changelist")},
                    {"label": "Products", "href": reverse("admin:catalog_product_changelist")},
                    {"label": "Add Product", "href": reverse("admin:catalog_product_add")},
                ],
            },
            {
                "title": "Pharmacist",
                "description": "Handle prescription review queues and customer clarifications.",
                "links": [
                    {"label": "Pending Reviews", "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review"},
                    {"label": "Clarifications", "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=clarification_required"},
                    {"label": "Review History", "href": reverse("admin:prescriptions_prescriptionreview_changelist")},
                ],
            },
            {
                "title": "Operations",
                "description": "Track order movement, payments, and day-to-day fulfillment work.",
                "links": [
                    {"label": "Orders", "href": reverse("admin:orders_order_changelist")},
                    {"label": "Payment Attempts", "href": reverse("admin:orders_paymentattempt_changelist")},
                    {"label": "Settlement Batches", "href": reverse("admin:orders_settlementbatch_changelist")},
                ],
            },
        ],
        "spotlight_panels": [
            {
                "title": "Operations Queue",
                "items": [
                    {
                        "label": "Pending prescription reviews",
                        "value": Prescription.objects.filter(status="pending_review").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=pending_review",
                    },
                    {
                        "label": "Clarification required",
                        "value": Prescription.objects.filter(status="clarification_required").count(),
                        "href": f"{reverse('admin:prescriptions_prescription_changelist')}?status__exact=clarification_required",
                    },
                    {
                        "label": "Orders pending prescription review",
                        "value": Order.objects.filter(status="pending_prescription_review").count(),
                        "href": f"{reverse('admin:orders_order_changelist')}?status__exact=pending_prescription_review",
                    },
                ],
            },
            {
                "title": "Business Snapshot",
                "items": [
                    {
                        "label": "Pending approvals",
                        "value": pending_approvals,
                        "href": reverse("admin-approval-queue"),
                    },
                    {
                        "label": "Total customers",
                        "value": User.objects.filter(role="customer").count(),
                        "href": f"{reverse('admin:users_user_changelist')}?role__exact=customer",
                    },
                    {
                        "label": "Catalog managers and pharmacists",
                        "value": User.objects.filter(role__in=["catalog_manager", "pharmacist"]).count(),
                        "href": reverse("admin:users_user_changelist"),
                    },
                    {
                        "label": "Confirmed orders",
                        "value": Order.objects.filter(status="confirmed").count(),
                        "href": f"{reverse('admin:orders_order_changelist')}?status__exact=confirmed",
                    },
                ],
            },
            {
                "title": "Inventory Risk",
                "items": [
                    {
                        "label": "Low stock products",
                        "value": inventory_risk["low_stock_count"],
                        "href": f"{reverse('admin:catalog_product_changelist')}?stock_status__exact=low_stock",
                    },
                    {
                        "label": "Out of stock products",
                        "value": inventory_risk["out_of_stock_count"],
                        "href": f"{reverse('admin:catalog_product_changelist')}?stock_status__exact=out_of_stock",
                    },
                    {
                        "label": "Inventory rows",
                        "value": Product.objects.filter(inventory_items__isnull=False).distinct().count(),
                        "href": reverse("admin:inventory_inventoryitem_changelist"),
                    },
                ],
            },
        ],
        "performance_rings": performance_rings,
        "system_health_panels": system_health_panels,
        "pending_approval_users": pending_approval_users,
        "overdue_approval_users": overdue_approval_users,
        "overdue_approval_by_owner": overdue_approval_by_owner,
        "recent_approval_escalations": recent_approval_escalations,
        "dashboard_approval_presets": dashboard_approval_presets,
        "approval_preset_tiles": approval_preset_tiles,
        "approval_reviewer_workloads": approval_reviewer_workloads[:6],
        "activity_feed": activity_feed,
        "recent_orders": recent_orders,
        "recent_prescriptions": recent_prescriptions,
        "app_list": app_list,
        "command_items": command_items,
        "dashboard_live_url": reverse("admin-dashboard-live"),
        "dashboard_last_updated": timezone.localtime().strftime("%d %b %Y %I:%M:%S %p"),
    }


@admin.site.admin_view
def admin_dashboard(request):
    return render(request, "admin/dashboard.html", _dashboard_context(request))


@admin.site.admin_view
def admin_dashboard_live(request):
    context = _dashboard_context(request)
    return JsonResponse(
        {
            "timestamp": context["dashboard_last_updated"],
            "kpis": {tile["label"]: str(tile["value"]) for tile in context["kpi_tiles"]},
            "business": {tile["label"]: str(tile["value"]) for tile in context["business_tiles"]},
            "today": {tile["label"]: str(tile["value"]) for tile in context["today_tiles"]},
            "alerts": {tile["label"]: str(tile["value"]) for tile in context["alert_tiles"]},
            "health": {panel["label"]: panel["status"] for panel in context["system_health_panels"]},
            "feed": context["activity_feed"][:5],
            "notifications": context["notification_panels"][:4],
            "audit": context["audit_timeline"][:4],
        }
    )


def _can_manage_approvals(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "role", "") in {"admin", "super_admin"})


def _build_approval_timeline(user_ids, *, limit: int | None = None):
    from platform_apps.audit.models import AuditLog

    normalized_ids = [int(user_id) for user_id in user_ids if user_id]
    if not normalized_ids:
        return {}

    audit_rows = list(
        AuditLog.objects.filter(entity_type="user", entity_id__in=[str(user_id) for user_id in normalized_ids]).order_by("-created_at")
    )
    timeline_by_user: dict[int, list[dict]] = {user_id: [] for user_id in normalized_ids}
    for entry in audit_rows:
        try:
            user_id = int(entry.entity_id)
        except (TypeError, ValueError):
            continue
        if user_id not in timeline_by_user:
            continue
        if limit is not None and len(timeline_by_user[user_id]) >= limit:
            continue
        timeline_by_user[user_id].append(
            {
                "event_type": entry.event_type,
                "message": entry.message,
                "actor_label": entry.actor_label or "System",
                "timestamp": timezone.localtime(entry.created_at).strftime("%d %b %I:%M %p"),
            }
        )
    return timeline_by_user


def _approval_redirect_target(request, fallback: str, user_id: int | None = None):
    return request.POST.get("next") or (reverse("admin-approval-detail", args=[user_id]) if user_id else fallback)


def _approval_queue_filter_params(request):
    assigned_to = request.GET.get("assigned_to", "").strip()
    overdue_only = request.GET.get("overdue", "").strip() in {"1", "true", "yes"}
    escalated_only = request.GET.get("escalated", "").strip() in {"1", "true", "yes"}
    document_rejected_only = request.GET.get("document_rejected", "").strip() in {"1", "true", "yes"}
    return {
        "assigned_to": assigned_to,
        "overdue_only": overdue_only,
        "escalated_only": escalated_only,
        "document_rejected_only": document_rejected_only,
    }


def _approval_queue_url(
    base_url: str,
    *,
    assigned_to: str = "",
    overdue_only: bool = False,
    escalated_only: bool = False,
    document_rejected_only: bool = False,
):
    params = []
    if assigned_to:
        params.append(f"assigned_to={assigned_to}")
    if overdue_only:
        params.append("overdue=1")
    if escalated_only:
        params.append("escalated=1")
    if document_rejected_only:
        params.append("document_rejected=1")
    return f"{base_url}?{'&'.join(params)}" if params else base_url


def _approval_queue_presets(user, base_url: str):
    current_user_id = str(user.pk)
    return [
        {
            "label": "All pending",
            "description": "Open the full approval backlog.",
            "href": base_url,
        },
        {
            "label": "My queue",
            "description": "Requests currently assigned to you.",
            "href": _approval_queue_url(base_url, assigned_to=current_user_id),
        },
        {
            "label": "My overdue",
            "description": "Your approvals that have crossed SLA.",
            "href": _approval_queue_url(base_url, assigned_to=current_user_id, overdue_only=True),
        },
        {
            "label": "Unassigned",
            "description": "Requests waiting for an owner.",
            "href": _approval_queue_url(base_url, assigned_to="unassigned"),
        },
        {
            "label": "Escalated",
            "description": "Recently escalated approval requests.",
            "href": _approval_queue_url(base_url, escalated_only=True),
        },
        {
            "label": "Document rejected",
            "description": "Pending requests with rejected proof documents.",
            "href": _approval_queue_url(base_url, document_rejected_only=True),
        },
    ]


def _approval_reviewer_queryset():
    from platform_apps.users.models import User

    return User.objects.filter(Q(is_superuser=True) | Q(role__in=["admin", "super_admin"])).order_by("full_name", "email", "phone_number")


def _approval_reviewer_workload_rows(base_url: str):
    from platform_apps.users.models import User

    now = timezone.now()
    workload_rows = []
    for reviewer in _approval_reviewer_queryset():
        if not reviewer.is_available_for_approval_assignment:
            continue
        assigned_queue = User.objects.filter(
            approval_status="pending",
            role__in=["vendor", "pharmacist"],
            approval_assigned_to=reviewer,
        )
        pending_count = assigned_queue.count()
        overdue_count = assigned_queue.filter(approval_due_at__isnull=False, approval_due_at__lt=now).count()
        reviewer_label = str(reviewer)
        workload_rows.append(
            {
                "reviewer": reviewer,
                "label": reviewer_label,
                "specialty": reviewer.approval_specialty,
                "specialty_label": reviewer.get_approval_specialty_display(),
                "availability_label": "Available",
                "pending_count": pending_count,
                "overdue_count": overdue_count,
                "load_score": (overdue_count * 100) + pending_count,
                "href": _approval_queue_url(base_url, assigned_to=str(reviewer.pk)),
            }
        )
    return sorted(workload_rows, key=lambda item: (item["load_score"], item["pending_count"], item["label"]))


def _recommended_approval_reviewer(workload_rows, *, approval_role: str | None = None):
    if not workload_rows:
        return None
    if approval_role:
        exact_matches = [row for row in workload_rows if row["specialty"] == approval_role]
        if exact_matches:
            return exact_matches[0]
        fallback_matches = [row for row in workload_rows if row["specialty"] == "all"]
        if fallback_matches:
            return fallback_matches[0]
    return workload_rows[0]


def _apply_assignment_sla(user):
    user.approval_sla_state_value = user.approval_sla_state
    user.approval_assignee_label = str(user.approval_assigned_to) if user.approval_assigned_to else "Unassigned"
    user.approval_due_label = timezone.localtime(user.approval_due_at).strftime("%d %b %I:%M %p") if user.approval_due_at else "Not scheduled"
    return user


def _reviewer_availability_label(reviewer) -> str:
    current_time = timezone.localtime()
    if reviewer.approval_unavailable_until and reviewer.approval_unavailable_until > timezone.now():
        return f"Unavailable until {timezone.localtime(reviewer.approval_unavailable_until).strftime('%d %b %I:%M %p')}"
    if not reviewer.approval_available_for_assignment:
        return "Unavailable"
    if current_time.date() in reviewer.approval_leave_date_list:
        return f"On leave ({current_time.strftime('%d %b')})"
    if not reviewer.is_within_approval_shift():
        return (
            f"Off shift ({reviewer.approval_shift_start_hour:02d}:00-{reviewer.approval_shift_end_hour:02d}:00)"
        )
    return "Available"


def _reviewer_schedule_rows(queue_base_url: str):
    from platform_apps.users.models import User

    now = timezone.now()
    rows = []
    for reviewer in _approval_reviewer_queryset():
        assigned_queue = User.objects.filter(
            approval_status="pending",
            role__in=["vendor", "pharmacist"],
            approval_assigned_to=reviewer,
        )
        rows.append(
            {
                "reviewer": reviewer,
                "assigned_count": assigned_queue.count(),
                "overdue_count": assigned_queue.filter(approval_due_at__isnull=False, approval_due_at__lt=now).count(),
                "availability_label": _reviewer_availability_label(reviewer),
                "queue_href": _approval_queue_url(queue_base_url, assigned_to=str(reviewer.pk)),
                "shift_weekday_values": {str(value) for value in reviewer.approval_shift_weekday_list},
                "leave_dates_value": reviewer.approval_leave_dates,
                "unavailable_until_value": (
                    timezone.localtime(reviewer.approval_unavailable_until).strftime("%Y-%m-%dT%H:%M")
                    if reviewer.approval_unavailable_until
                    else ""
                ),
            }
        )
    return rows


def _escalate_overdue_approvals(users, *, actor=None):
    from platform_apps.users.services import notify_overdue_approval_escalation

    for user in users:
        notify_overdue_approval_escalation(user, actor=actor)


def _filtered_approval_queue_queryset(filter_state):
    from platform_apps.users.models import User

    queue_queryset = User.objects.filter(approval_status="pending", role__in=["vendor", "pharmacist"])
    if filter_state["assigned_to"]:
        if filter_state["assigned_to"] == "unassigned":
            queue_queryset = queue_queryset.filter(approval_assigned_to__isnull=True)
        else:
            queue_queryset = queue_queryset.filter(approval_assigned_to_id=filter_state["assigned_to"])
    if filter_state["overdue_only"]:
        queue_queryset = queue_queryset.filter(approval_due_at__isnull=False, approval_due_at__lt=timezone.now())
    if filter_state["escalated_only"]:
        queue_queryset = queue_queryset.filter(approval_last_escalated_at__isnull=False)
    if filter_state["document_rejected_only"]:
        queue_queryset = queue_queryset.filter(
            Q(role="vendor", vendor_license_document_status="rejected")
            | Q(role="pharmacist", pharmacist_registration_document_status="rejected")
        )
    return queue_queryset


def _handle_approval_queue_action(request, *, success_redirect: str):
    from platform_apps.audit.models import AuditLog
    from platform_apps.users.models import User
    from platform_apps.users.services import notify_user_of_approval_decision

    bulk_action = request.POST.get("bulk_action", "").strip()
    if bulk_action:
        filter_state = {
            "assigned_to": request.POST.get("filter_assigned_to", "").strip(),
            "overdue_only": request.POST.get("filter_overdue", "").strip() in {"1", "true", "yes"},
            "escalated_only": request.POST.get("filter_escalated", "").strip() in {"1", "true", "yes"},
            "document_rejected_only": request.POST.get("filter_document_rejected", "").strip() in {"1", "true", "yes"},
        }
        bulk_queryset = _filtered_approval_queue_queryset(filter_state)
        if bulk_action == "bulk_claim_visible":
            updated_count = bulk_queryset.update(
                approval_assigned_to=request.user,
                approval_assigned_at=timezone.now(),
                updated_at=timezone.now(),
            )
            messages.success(request, f"Claimed {updated_count} visible approval request(s).")
            return redirect(success_redirect)
        if bulk_action == "bulk_assign_visible":
            reviewer_id = request.POST.get("assigned_reviewer_id", "").strip()
            selected_reviewer = get_object_or_404(_approval_reviewer_queryset(), pk=reviewer_id)
            updated_count = bulk_queryset.update(
                approval_assigned_to=selected_reviewer,
                approval_assigned_at=timezone.now(),
                updated_at=timezone.now(),
            )
            messages.success(request, f"Assigned {updated_count} visible approval request(s) to {selected_reviewer}.")
            return redirect(success_redirect)
        if bulk_action == "bulk_assign_suggested_visible":
            workload_rows = _approval_reviewer_workload_rows(reverse("admin-approval-queue"))
            assignment_timestamp = timezone.now()
            updated_count = 0
            for target_user in bulk_queryset.filter(approval_assigned_to__isnull=True).order_by("created_at"):
                selected_workload = _recommended_approval_reviewer(workload_rows, approval_role=target_user.role)
                if selected_workload is None:
                    break
                selected_reviewer = selected_workload["reviewer"]
                target_user.approval_assigned_to = selected_reviewer
                target_user.approval_assigned_at = assignment_timestamp
                target_user.save(update_fields=["approval_assigned_to", "approval_assigned_at", "updated_at"])
                AuditLog.objects.create(
                    actor=request.user,
                    actor_label=str(request.user),
                    event_type="approval_assignment_changed",
                    entity_type="user",
                    entity_id=str(target_user.pk),
                    message=f"Approval request auto-assigned to {selected_reviewer} for {target_user.email or target_user.phone_number}.",
                    meta={
                        "assigned_reviewer_id": selected_reviewer.pk,
                        "assigned_reviewer_label": str(selected_reviewer),
                        "assignment_mode": "suggested",
                        "reviewer_specialty": selected_reviewer.approval_specialty,
                        "bulk_action": bulk_action,
                    },
                )
                selected_workload["pending_count"] += 1
                selected_workload["load_score"] += 1
                workload_rows = sorted(workload_rows, key=lambda item: (item["load_score"], item["pending_count"], item["label"]))
                updated_count += 1
            messages.success(request, f"Auto-assigned {updated_count} visible approval request(s) using reviewer workload balancing.")
            return redirect(success_redirect)
        if bulk_action in {"bulk_verify_visible_documents", "bulk_reject_visible_documents"}:
            document_decision = "verified" if bulk_action == "bulk_verify_visible_documents" else "rejected"
            approval_notes = request.POST.get("approval_notes", "").strip()
            updated_count = 0
            reviewed_at = timezone.now()
            for target_user in bulk_queryset.iterator():
                document_field = {
                    "vendor": "vendor_license_document_status",
                    "pharmacist": "pharmacist_registration_document_status",
                }.get(target_user.role)
                if not document_field:
                    continue
                setattr(target_user, document_field, document_decision)
                target_user.approval_notes = approval_notes
                target_user.approval_reviewed_by = request.user
                target_user.approval_reviewed_at = reviewed_at
                target_user.save(
                    update_fields=[document_field, "approval_notes", "approval_reviewed_by", "approval_reviewed_at", "updated_at"]
                )
                AuditLog.objects.create(
                    actor=request.user,
                    actor_label=str(request.user),
                    event_type="approval_document_status_changed",
                    entity_type="user",
                    entity_id=str(target_user.pk),
                    message=f"{target_user.get_role_display()} document marked as {document_decision} for {target_user.email or target_user.phone_number}.",
                    meta={
                        "document_kind": target_user.role,
                        "document_status": document_decision,
                        "approval_notes": approval_notes,
                        "bulk_action": bulk_action,
                    },
                )
                updated_count += 1
            messages.success(request, f"Marked {updated_count} visible document(s) as {document_decision}.")
            return redirect(success_redirect)
        messages.error(request, "Invalid bulk action.")
        return redirect(success_redirect)

    user_id = request.POST.get("user_id", "").strip()
    decision = request.POST.get("decision", "").strip()
    approval_notes = request.POST.get("approval_notes", "").strip()
    target_user = get_object_or_404(User, pk=user_id, approval_status="pending", role__in=["vendor", "pharmacist"])
    document_kind = request.POST.get("document_kind", "").strip()
    document_decision = request.POST.get("document_decision", "").strip()
    assignment_action = request.POST.get("assignment_action", "").strip()

    if assignment_action:
        selected_reviewer = None
        if assignment_action == "claim":
            selected_reviewer = request.user
        elif assignment_action == "unassign":
            selected_reviewer = None
        elif assignment_action == "assign":
            reviewer_id = request.POST.get("assigned_reviewer_id", "").strip()
            selected_reviewer = get_object_or_404(_approval_reviewer_queryset(), pk=reviewer_id)
        elif assignment_action == "assign_suggested":
            selected_workload = _recommended_approval_reviewer(
                _approval_reviewer_workload_rows(reverse("admin-approval-queue")),
                approval_role=target_user.role,
            )
            if selected_workload is None:
                messages.error(request, "No reviewer is available for suggested assignment.")
                return redirect(success_redirect)
            selected_reviewer = selected_workload["reviewer"]
        else:
            messages.error(request, "Invalid assignment action.")
            return redirect(success_redirect)

        target_user.approval_assigned_to = selected_reviewer
        target_user.approval_assigned_at = timezone.now() if selected_reviewer else None
        target_user.save(update_fields=["approval_assigned_to", "approval_assigned_at", "updated_at"])
        AuditLog.objects.create(
            actor=request.user,
            actor_label=str(request.user),
            event_type="approval_assignment_changed",
            entity_type="user",
            entity_id=str(target_user.pk),
            message=(
                f"Approval request assigned to {selected_reviewer} for {target_user.email or target_user.phone_number}."
                if selected_reviewer
                else f"Approval request unassigned for {target_user.email or target_user.phone_number}."
            ),
            meta={
                "assigned_reviewer_id": selected_reviewer.pk if selected_reviewer else None,
                "assigned_reviewer_label": str(selected_reviewer) if selected_reviewer else None,
                "assignment_mode": "suggested" if assignment_action == "assign_suggested" else "manual",
                "reviewer_specialty": selected_reviewer.approval_specialty if selected_reviewer else None,
            },
        )
        messages.success(request, f"Reviewer updated for {target_user.email or target_user.phone_number}.")
        return redirect(success_redirect)

    if document_kind and document_decision:
        document_field = {
            "vendor": "vendor_license_document_status",
            "pharmacist": "pharmacist_registration_document_status",
        }.get(document_kind)
        if document_field is None or document_decision not in {"verified", "rejected"}:
            messages.error(request, "Invalid document verification action.")
            return redirect(success_redirect)

        setattr(target_user, document_field, document_decision)
        target_user.approval_notes = approval_notes
        target_user.approval_reviewed_by = request.user
        target_user.approval_reviewed_at = timezone.now()
        target_user.save(
            update_fields=[document_field, "approval_notes", "approval_reviewed_by", "approval_reviewed_at", "updated_at"]
        )
        AuditLog.objects.create(
            actor=request.user,
            actor_label=str(request.user),
            event_type="approval_document_status_changed",
            entity_type="user",
            entity_id=str(target_user.pk),
            message=f"{document_kind.title()} document marked as {document_decision} for {target_user.email or target_user.phone_number}.",
            meta={
                "document_kind": document_kind,
                "document_status": document_decision,
                "approval_notes": approval_notes,
            },
        )
        messages.success(request, f"{document_kind.title()} document marked as {document_decision}.")
        return redirect(success_redirect)

    if decision not in {"approved", "rejected"}:
        messages.error(request, "Invalid approval action.")
        return redirect(success_redirect)
    if decision == "approved" and not target_user.documents_ready_for_approval:
        messages.error(request, "Required proof documents must be verified before approval.")
        return redirect(success_redirect)

    previous_status = target_user.approval_status
    target_user.approval_status = decision
    target_user.approval_notes = approval_notes
    target_user.approval_reviewed_by = request.user
    target_user.approval_reviewed_at = timezone.now()
    target_user.save(update_fields=["approval_status", "approval_notes", "approval_reviewed_by", "approval_reviewed_at", "updated_at"])
    notify_user_of_approval_decision(target_user, previous_status=previous_status, actor=request.user)
    messages.success(request, f"{target_user.email or target_user.phone_number} marked as {decision}.")
    return redirect(success_redirect)


@admin.site.admin_view
def admin_approval_queue(request):
    from platform_apps.users.models import User

    if not _can_manage_approvals(request.user):
        return HttpResponseForbidden("Access denied")

    if request.method == "POST":
        return _handle_approval_queue_action(request, success_redirect=_approval_redirect_target(request, reverse("admin-approval-queue")))

    filter_state = _approval_queue_filter_params(request)
    queue = list(_filtered_approval_queue_queryset(filter_state).order_by("created_at"))
    reviewer_workloads = _approval_reviewer_workload_rows(reverse("admin-approval-queue"))
    reviewers = list(_approval_reviewer_queryset())
    for reviewer in reviewers:
        reviewer.approval_availability_label = _reviewer_availability_label(reviewer)
    _escalate_overdue_approvals(queue, actor=request.user)
    timeline_by_user = _build_approval_timeline([user.pk for user in queue], limit=4)
    for user in queue:
        user.approval_timeline = timeline_by_user.get(user.pk, [])
        _apply_assignment_sla(user)
        if user.approval_assigned_to_id is None:
            suggested_workload = _recommended_approval_reviewer(reviewer_workloads, approval_role=user.role)
            if suggested_workload is not None:
                user.suggested_reviewer = suggested_workload["reviewer"]
                user.suggested_reviewer_label = suggested_workload["label"]
                user.suggested_reviewer_specialty_label = suggested_workload["specialty_label"]
    return render(
        request,
        "admin/approval_queue.html",
        {
            **admin.site.each_context(request),
            "title": "Approval Queue",
            "queue": queue,
            "queue_count": len(queue),
            "reviewers": reviewers,
            "reviewer_workloads": reviewer_workloads,
            "filter_state": filter_state,
            "queue_base_url": reverse("admin-approval-queue"),
            "queue_presets": _approval_queue_presets(request.user, reverse("admin-approval-queue")),
        },
    )


@admin.site.admin_view
def admin_reviewer_schedules(request):
    from platform_apps.audit.models import AuditLog

    if not _can_manage_approvals(request.user):
        return HttpResponseForbidden("Access denied")

    if request.method == "POST":
        reviewer = get_object_or_404(_approval_reviewer_queryset(), pk=request.POST.get("reviewer_id", "").strip())
        reviewer.approval_specialty = request.POST.get("approval_specialty", reviewer.approval_specialty).strip() or reviewer.approval_specialty
        reviewer.approval_available_for_assignment = request.POST.get("approval_available_for_assignment") == "on"

        unavailable_until_raw = request.POST.get("approval_unavailable_until", "").strip()
        if unavailable_until_raw:
            parsed_unavailable_until = parse_datetime(unavailable_until_raw)
            if parsed_unavailable_until is None:
                messages.error(request, "Invalid unavailable-until timestamp.")
                return redirect(reverse("admin-reviewer-schedules"))
            if timezone.is_naive(parsed_unavailable_until):
                parsed_unavailable_until = timezone.make_aware(parsed_unavailable_until, timezone.get_current_timezone())
            reviewer.approval_unavailable_until = parsed_unavailable_until
        else:
            reviewer.approval_unavailable_until = None

        reviewer.approval_shift_start_hour = max(0, min(23, int(request.POST.get("approval_shift_start_hour", reviewer.approval_shift_start_hour))))
        reviewer.approval_shift_end_hour = max(0, min(23, int(request.POST.get("approval_shift_end_hour", reviewer.approval_shift_end_hour))))

        weekday_values = sorted(
            {
                str(int(value))
                for value in request.POST.getlist("approval_shift_weekdays")
                if value.strip().isdigit() and 0 <= int(value) <= 6
            }
        )
        reviewer.approval_shift_weekdays = ",".join(weekday_values)

        leave_dates = []
        for raw_value in request.POST.get("approval_leave_dates", "").split(","):
            raw_value = raw_value.strip()
            if not raw_value:
                continue
            try:
                timezone.datetime.fromisoformat(raw_value)
            except ValueError:
                messages.error(request, "Leave dates must use YYYY-MM-DD format.")
                return redirect(reverse("admin-reviewer-schedules"))
            leave_dates.append(raw_value)
        reviewer.approval_leave_dates = ",".join(sorted(set(leave_dates)))
        reviewer.save(
            update_fields=[
                "approval_specialty",
                "approval_available_for_assignment",
                "approval_unavailable_until",
                "approval_shift_start_hour",
                "approval_shift_end_hour",
                "approval_shift_weekdays",
                "approval_leave_dates",
                "updated_at",
            ]
        )
        AuditLog.objects.create(
            actor=request.user,
            actor_label=str(request.user),
            event_type="reviewer_schedule_updated",
            entity_type="user",
            entity_id=str(reviewer.pk),
            message=f"Updated reviewer schedule for {reviewer.email or reviewer.phone_number}.",
            meta={
                "approval_specialty": reviewer.approval_specialty,
                "approval_available_for_assignment": reviewer.approval_available_for_assignment,
                "approval_shift_start_hour": reviewer.approval_shift_start_hour,
                "approval_shift_end_hour": reviewer.approval_shift_end_hour,
                "approval_shift_weekdays": reviewer.approval_shift_weekdays,
                "approval_leave_dates": reviewer.approval_leave_dates,
            },
        )
        messages.success(request, f"Reviewer schedule updated for {reviewer}.")
        return redirect(reverse("admin-reviewer-schedules"))

    queue_base_url = reverse("admin-approval-queue")
    reviewer_rows = _reviewer_schedule_rows(queue_base_url)
    return render(
        request,
        "admin/reviewer_schedules.html",
        {
            **admin.site.each_context(request),
            "title": "Reviewer Schedules",
            "reviewer_rows": reviewer_rows,
            "queue_base_url": queue_base_url,
            "weekday_choices": [
                ("0", "Mon"),
                ("1", "Tue"),
                ("2", "Wed"),
                ("3", "Thu"),
                ("4", "Fri"),
                ("5", "Sat"),
                ("6", "Sun"),
            ],
            "specialty_choices": [
                ("all", "All Approval Types"),
                ("vendor", "Vendor Reviews"),
                ("pharmacist", "Pharmacist Reviews"),
            ],
        },
    )


@admin.site.admin_view
def approval_queue_export(request):
    if not _can_manage_approvals(request.user):
        return HttpResponseForbidden("Access denied")

    filter_state = _approval_queue_filter_params(request)
    queue = list(_filtered_approval_queue_queryset(filter_state).order_by("created_at"))
    for user in queue:
        _apply_assignment_sla(user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="approval-queue-export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "full_name",
            "email",
            "phone_number",
            "role",
            "approval_status",
            "assigned_reviewer",
            "sla_state",
            "approval_due_at",
            "vendor_license_document_status",
            "pharmacist_registration_document_status",
            "created_at",
        ]
    )
    for user in queue:
        writer.writerow(
            [
                user.full_name or "",
                user.email or "",
                user.phone_number,
                user.role,
                user.approval_status,
                user.approval_assignee_label,
                user.approval_sla_state_value,
                timezone.localtime(user.approval_due_at).strftime("%Y-%m-%d %H:%M:%S") if user.approval_due_at else "",
                user.vendor_license_document_status,
                user.pharmacist_registration_document_status,
                timezone.localtime(user.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )
    return response


@admin.site.admin_view
def admin_approval_detail(request, user_id: int):
    from platform_apps.users.models import User

    if not _can_manage_approvals(request.user):
        return HttpResponseForbidden("Access denied")

    target_user = get_object_or_404(User, pk=user_id, role__in=["vendor", "pharmacist"])

    if request.method == "POST":
        return _handle_approval_queue_action(
            request,
            success_redirect=_approval_redirect_target(request, reverse("admin-approval-detail", args=[target_user.pk]), target_user.pk),
        )

    target_user.approval_timeline = _build_approval_timeline([target_user.pk]).get(target_user.pk, [])
    _escalate_overdue_approvals([target_user], actor=request.user)
    _apply_assignment_sla(target_user)
    reviewers = list(_approval_reviewer_queryset())
    for reviewer in reviewers:
        reviewer.approval_availability_label = _reviewer_availability_label(reviewer)
    return render(
        request,
        "admin/approval_detail.html",
        {
            **admin.site.each_context(request),
            "title": "Approval Request Detail",
            "target_user": target_user,
            "reviewers": reviewers,
        },
    )


@admin.site.admin_view
def approval_document_download(request, user_id: int, document_kind: str):
    from platform_apps.audit.models import AuditLog
    from platform_apps.users.models import User

    if not _can_manage_approvals(request.user):
        return HttpResponseForbidden("Access denied")

    target_user = get_object_or_404(User, pk=user_id)
    field_name = {
        "vendor": "vendor_license_document",
        "pharmacist": "pharmacist_registration_document",
    }.get(document_kind)
    if not field_name:
        return HttpResponseForbidden("Invalid document type")

    file_field = getattr(target_user, field_name)
    if not file_field:
        return HttpResponseForbidden("Document not found")

    AuditLog.objects.create(
        actor=request.user,
        actor_label=str(request.user),
        event_type="approval_document_downloaded",
        entity_type="user",
        entity_id=str(target_user.pk),
        message=f"Downloaded approval document for {target_user.email or target_user.phone_number}",
        meta={"document_kind": document_kind, "filename": file_field.name},
    )
    return FileResponse(file_field.open("rb"), as_attachment=True, filename=file_field.name.split("/")[-1])


@admin.site.admin_view
def managed_file_download(request, file_id: int):
    from platform_apps.audit.models import AuditLog, ManagedFile

    managed_file = get_object_or_404(ManagedFile.objects.select_related("uploaded_by"), pk=file_id)
    managed_file.download_count += 1
    managed_file.save(update_fields=["download_count", "updated_at"])
    AuditLog.objects.create(
        actor=request.user,
        actor_label=str(request.user),
        event_type="file_downloaded",
        entity_type="managed_file",
        entity_id=str(managed_file.pk),
        message=f"Downloaded file {managed_file.title}",
        meta={"filename": managed_file.filename},
    )
    return FileResponse(managed_file.file.open("rb"), as_attachment=True, filename=managed_file.filename)


urlpatterns = [
    path("", api_root),
    path("", include("platform_apps.users.web_urls")),
    path("auditor/", include("platform_apps.users.auditor_urls")),
    path("catalog/", include("platform_apps.users.catalog_urls")),
    path("compliance/", include("platform_apps.users.compliance_urls")),
    path("doctor/", include("platform_apps.users.doctor_urls")),
    path("marketing/", include("platform_apps.users.marketing_urls")),
    path("operations/", include("platform_apps.users.operations_urls")),
    path("procurement/", include("platform_apps.users.procurement_urls")),
    path("pharmacist/", include("platform_apps.users.pharmacist_urls")),
    path("vendor/", include("platform_apps.users.vendor_urls")),
    path("vendor-staff/", include("platform_apps.users.vendor_staff_urls")),
    path("warehouse/", include("platform_apps.users.warehouse_urls")),
    path("delivery/", include("platform_apps.users.delivery_urls")),
    path("support/", include("platform_apps.users.support_urls")),
    path("finance/", include("platform_apps.users.finance_urls")),
    path("security/", include("platform_apps.users.security_urls")),
    path("viewer/", include("platform_apps.users.viewer_urls")),
    path("admin/", include("platform_apps.users.admin_urls")),
    path("super-admin/", include("platform_apps.users.super_admin_urls")),
    path("admin/", admin_dashboard, name="admin-dashboard"),
    path("admin/reviewer-schedules/", admin_reviewer_schedules, name="admin-reviewer-schedules"),
    path("admin/approval-queue/", admin_approval_queue, name="admin-approval-queue"),
    path("admin/approval-queue/export/", approval_queue_export, name="admin-approval-queue-export"),
    path("admin/approval-queue/<int:user_id>/", admin_approval_detail, name="admin-approval-detail"),
    path("admin/approval-documents/<int:user_id>/<str:document_kind>/download/", approval_document_download, name="admin-approval-document-download"),
    path("admin/live/", admin_dashboard_live, name="admin-dashboard-live"),
    path("admin/files/<int:file_id>/download/", managed_file_download, name="admin-managed-file-download"),
    path("admin/", admin.site.urls),
    path("api/v1/health/", include("platform_apps.health.urls")),
    path("api/v1/auth/", include("platform_apps.users.urls")),
    path("api/v1/catalog/", include("platform_apps.catalog.urls")),
    path("api/v1/inventory/", include("platform_apps.inventory.urls")),
    path("api/v1/delivery/", include("platform_apps.delivery.urls")),
    path("api/v1/prescriptions/", include("platform_apps.prescriptions.urls")),
    path("api/v1/cart/", include("platform_apps.cart.urls")),
    path("api/v1/orders/", include("platform_apps.orders.urls")),
    path("api/v1/notifications/", include("platform_apps.notifications.urls")),
]
