from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from platform_apps.audit.services import record_audit_event
from platform_apps.notifications.services import create_notification
from platform_apps.users.models import User

from .models import DeliveryEvent, DeliveryShipment, DeliveryZone


def find_delivery_zone_for_pincode(pincode: str) -> DeliveryZone | None:
    normalized = "".join(ch for ch in str(pincode) if ch.isdigit())
    if not normalized:
        return None
    for length in range(min(6, len(normalized)), 0, -1):
        zone = DeliveryZone.objects.filter(is_active=True, pincode_prefix=normalized[:length]).first()
        if zone:
            return zone
    return None


def estimate_delivery_window(*, zone: DeliveryZone | None):
    if not zone:
        return None, None
    start = timezone.now() + timezone.timedelta(hours=zone.eta_min_hours)
    end = timezone.now() + timezone.timedelta(hours=zone.eta_max_hours)
    return start, end


def next_reattempt_time(*, shipment: DeliveryShipment) -> timezone.datetime:
    return timezone.now() + timezone.timedelta(hours=12 if shipment.service_level == "express" else 24)


def choose_service_level_for_order(order, *, zone: DeliveryZone | None) -> str:
    if zone and zone.eta_max_hours <= 24:
        return "express"
    if float(order.total) >= 1000:
        return "express"
    return "standard"


def choose_carrier_for_order(order, *, zone: DeliveryZone | None, service_level: str) -> str:
    if order.payment_method == "COD":
        return "TrueCare COD Express" if service_level == "express" else "TrueCare COD Surface"
    if zone and zone.code in {"BLR", "MUM", "DEL", "HYD"}:
        return "TrueCare Metro Express" if service_level == "express" else "TrueCare Metro"
    return "TrueCare National"


def delivery_blockers_for_order(order, *, zone: DeliveryZone | None) -> list[str]:
    blockers: list[str] = []
    if order.status == "cancelled":
        blockers.append("Order cancelled")
    if order.fulfillment_status in {"cancelled", "returned"}:
        blockers.append(f"Fulfillment {order.fulfillment_status.replace('_', ' ')}")
    if order.requires_prescription_count > 0 and order.status == "pending_prescription_review":
        blockers.append("Prescription approval pending")
    if order.payment_method != "COD" and order.payment_status != "paid":
        blockers.append("Payment not captured")
    if order.payment_method == "COD" and zone and not zone.cod_available:
        blockers.append("COD not supported for destination")
    if order.inventory_status != "reserved":
        blockers.append(f"Inventory {order.inventory_status.replace('_', ' ')}")
    return blockers


def is_dispatch_ready(order, *, zone: DeliveryZone | None) -> bool:
    return not delivery_blockers_for_order(order, zone=zone)


def _auto_dispatch_status_for_order(order, *, zone: DeliveryZone | None) -> str:
    if order.status == "cancelled" or order.fulfillment_status == "cancelled":
        return "cancelled"
    if order.fulfillment_status == "returned":
        return "returned"
    if order.fulfillment_status == "delivered":
        return "delivered"
    if order.fulfillment_status == "shipped":
        return "in_transit"
    if order.fulfillment_status == "packed" or is_dispatch_ready(order, zone=zone):
        return "assigned"
    return "queued"


def ensure_delivery_zones_seeded() -> None:
    defaults = [
        {"code": "BLR", "name": "Bangalore Metro", "pincode_prefix": "560", "city": "Bangalore", "state": "Karnataka", "eta_min_hours": 8, "eta_max_hours": 24, "cod_available": True},
        {"code": "DEL", "name": "Delhi NCR", "pincode_prefix": "110", "city": "Delhi", "state": "Delhi", "eta_min_hours": 12, "eta_max_hours": 24, "cod_available": True},
        {"code": "MUM", "name": "Mumbai Metro", "pincode_prefix": "400", "city": "Mumbai", "state": "Maharashtra", "eta_min_hours": 12, "eta_max_hours": 24, "cod_available": True},
        {"code": "HYD", "name": "Hyderabad Metro", "pincode_prefix": "500", "city": "Hyderabad", "state": "Telangana", "eta_min_hours": 12, "eta_max_hours": 24, "cod_available": True},
        {"code": "NAT", "name": "National Coverage", "pincode_prefix": "1", "city": "India", "state": "", "eta_min_hours": 48, "eta_max_hours": 96, "cod_available": False},
    ]
    for row in defaults:
        DeliveryZone.objects.get_or_create(code=row["code"], defaults=row)


def _notify_delivery_ops(*, title: str, body: str, meta: dict | None = None) -> None:
    recipients = User.objects.filter(
        is_active=True,
        role__in=["admin", "warehouse_operator", "support_agent"],
    )
    for user in recipients.iterator():
        create_notification(
            user=user,
            kind="system_alert",
            title=title,
            body=body,
            link="/admin/delivery",
            meta=meta or {},
        )


def _notify_customer_delivery_exception(*, order, title: str, body: str, shipment_status: str) -> None:
    create_notification(
        user=order.user,
        kind="order_update",
        title=title,
        body=body,
        link=f"/account/orders/{order.order_number}",
        meta={"order_number": order.order_number, "shipment_status": shipment_status},
    )


def _record_delivery_event(*, shipment: DeliveryShipment, status: str, summary: str, actor=None, meta: dict | None = None) -> None:
    last_event = shipment.events.order_by("-created_at").first()
    if last_event and last_event.status == status and last_event.summary == summary:
        return
    DeliveryEvent.objects.create(
        shipment=shipment,
        status=status,
        summary=summary,
        meta=meta or {},
        created_by=actor,
    )


def ensure_order_shipment(order, *, actor=None, notes: str = "") -> DeliveryShipment:
    ensure_delivery_zones_seeded()
    zone = find_delivery_zone_for_pincode(order.pincode)
    eta_start, eta_end = estimate_delivery_window(zone=zone)
    service_level = choose_service_level_for_order(order, zone=zone)
    carrier_name = choose_carrier_for_order(order, zone=zone, service_level=service_level)
    computed_notes = notes or "; ".join(delivery_blockers_for_order(order, zone=zone))
    shipment, created = DeliveryShipment.objects.get_or_create(
        order=order,
        defaults={
            "zone": zone,
            "carrier_name": carrier_name,
            "service_level": service_level,
            "status": _auto_dispatch_status_for_order(order, zone=zone),
            "tracking_reference": order.tracking_reference,
            "eta_start": eta_start,
            "eta_end": eta_end,
            "status_notes": computed_notes,
        },
    )
    changed_fields = []
    if shipment.zone_id != getattr(zone, "id", None):
        shipment.zone = zone
        changed_fields.append("zone")
    if shipment.eta_start != eta_start:
        shipment.eta_start = eta_start
        changed_fields.append("eta_start")
    if shipment.eta_end != eta_end:
        shipment.eta_end = eta_end
        changed_fields.append("eta_end")
    if shipment.service_level != service_level:
        shipment.service_level = service_level
        changed_fields.append("service_level")
    if shipment.carrier_name != carrier_name:
        shipment.carrier_name = carrier_name
        changed_fields.append("carrier_name")
    if computed_notes and shipment.status_notes != computed_notes:
        shipment.status_notes = computed_notes
        changed_fields.append("status_notes")
    if order.tracking_reference and shipment.tracking_reference != order.tracking_reference:
        shipment.tracking_reference = order.tracking_reference
        changed_fields.append("tracking_reference")
    if changed_fields:
        changed_fields.append("updated_at")
        shipment.save(update_fields=changed_fields)
    if created:
        _record_delivery_event(
            shipment=shipment,
            status=shipment.status,
            summary="Shipment queue created for order.",
            actor=actor,
            meta={"order_number": order.order_number},
        )
    return shipment


def sync_delivery_for_order(order, *, actor=None, notes: str = "") -> DeliveryShipment:
    with transaction.atomic():
        shipment = ensure_order_shipment(order, actor=actor, notes=notes)
        previous_status = shipment.status
        previous_tracking = shipment.tracking_reference
        zone = shipment.zone

        if order.status == "cancelled" or order.fulfillment_status == "cancelled":
            shipment.status = "cancelled"
        elif order.fulfillment_status == "returned":
            shipment.status = "returned"
        elif order.fulfillment_status == "delivered":
            shipment.status = "delivered"
            if shipment.delivered_at is None:
                shipment.delivered_at = timezone.now()
        elif order.fulfillment_status == "shipped":
            shipment.status = "in_transit"
            if shipment.assigned_at is None:
                shipment.assigned_at = timezone.now()
            if shipment.dispatched_at is None:
                shipment.dispatched_at = timezone.now()
            if not shipment.tracking_reference:
                shipment.tracking_reference = order.tracking_reference or f"TRK-{order.order_number}"
        elif order.fulfillment_status == "packed" or is_dispatch_ready(order, zone=zone):
            shipment.status = "assigned"
            if shipment.assigned_at is None:
                shipment.assigned_at = timezone.now()
        else:
            shipment.status = "queued"

        update_fields = ["status", "updated_at"]
        if shipment.assigned_at and "assigned_at" not in update_fields:
            update_fields.append("assigned_at")
        if shipment.dispatched_at and "dispatched_at" not in update_fields:
            update_fields.append("dispatched_at")
        if shipment.delivered_at and "delivered_at" not in update_fields:
            update_fields.append("delivered_at")
        computed_notes = notes or "; ".join(delivery_blockers_for_order(order, zone=zone))
        if shipment.status_notes != computed_notes:
            shipment.status_notes = computed_notes
            update_fields.append("status_notes")
        if shipment.status in {"queued", "assigned", "picked_up", "in_transit", "out_for_delivery"} and shipment.failure_reason:
            shipment.failure_reason = ""
            update_fields.append("failure_reason")
        if shipment.status != "failed" and shipment.next_attempt_at is not None:
            shipment.next_attempt_at = None
            update_fields.append("next_attempt_at")
        if shipment.tracking_reference != order.tracking_reference and shipment.tracking_reference:
            order.tracking_reference = shipment.tracking_reference
            order.save(update_fields=["tracking_reference", "updated_at"])
        shipment.save(update_fields=list(dict.fromkeys(update_fields)))

        if shipment.status != previous_status or shipment.tracking_reference != previous_tracking:
            _record_delivery_event(
                shipment=shipment,
                status=shipment.status,
                summary=f"Shipment moved to {shipment.get_status_display().lower()}.",
                actor=actor,
                meta={"tracking_reference": shipment.tracking_reference, "order_number": order.order_number},
            )
            if shipment.status in {"in_transit", "delivered", "cancelled", "returned"}:
                _notify_customer_delivery_exception(
                    order=order,
                    title="Delivery update",
                    body=f"{order.order_number} delivery is now {shipment.get_status_display().lower()}.",
                    shipment_status=shipment.status,
                )
            if shipment.status == "cancelled":
                _notify_delivery_ops(
                    title="Shipment cancelled",
                    body=f"{order.order_number} left the delivery queue before dispatch.",
                    meta={"order_number": order.order_number},
                )
            if shipment.status == "assigned" and is_dispatch_ready(order, zone=zone):
                _notify_delivery_ops(
                    title="Dispatch-ready order",
                    body=f"{order.order_number} is ready for carrier handoff via {shipment.carrier_name}.",
                    meta={"order_number": order.order_number, "carrier_name": shipment.carrier_name},
                )
        return shipment


def apply_delivery_shipment_update(shipment: DeliveryShipment, *, actor=None, **validated_data) -> DeliveryShipment:
    from platform_apps.inventory.services import sync_order_inventory
    from platform_apps.orders.models import Order

    previous_status = shipment.status
    previous_tracking = shipment.tracking_reference
    previous_reattempt_count = shipment.reattempt_count
    order = Order.objects.get(pk=shipment.order_id)
    zone = shipment.zone
    blockers = delivery_blockers_for_order(order, zone=zone)
    next_status = validated_data.get("status", shipment.status)
    if next_status in {"assigned", "picked_up", "in_transit", "out_for_delivery"} and blockers:
        raise ValidationError({"status": f"Shipment is blocked: {', '.join(blockers)}."})
    for field, value in validated_data.items():
        setattr(shipment, field, value)

    if shipment.status == "assigned" and shipment.assigned_at is None:
        shipment.assigned_at = timezone.now()
    if shipment.status in {"in_transit", "out_for_delivery"} and shipment.dispatched_at is None:
        shipment.dispatched_at = timezone.now()
    if shipment.status == "delivered" and shipment.delivered_at is None:
        shipment.delivered_at = timezone.now()
    if shipment.status == "failed":
        shipment.failed_at = timezone.now()
        if not shipment.failure_reason:
            shipment.failure_reason = shipment.status_notes or "Delivery attempt failed"
        if shipment.next_attempt_at is None:
            shipment.next_attempt_at = next_reattempt_time(shipment=shipment)
    elif shipment.status == "queued" and previous_status == "failed":
        shipment.reattempt_count = shipment.reattempt_count + 1
        shipment.next_attempt_at = next_reattempt_time(shipment=shipment)
        shipment.failure_reason = ""
        shipment.failed_at = None
    elif shipment.status not in {"failed"}:
        shipment.next_attempt_at = None

    shipment.save()

    next_fulfillment = order.fulfillment_status
    if shipment.status == "queued":
        next_fulfillment = "queued"
    elif shipment.status in {"assigned", "picked_up"}:
        next_fulfillment = "packed"
    elif shipment.status in {"in_transit", "out_for_delivery"}:
        next_fulfillment = "shipped"
    elif shipment.status == "delivered":
        next_fulfillment = "delivered"
    elif shipment.status == "returned":
        next_fulfillment = "returned"
    elif shipment.status == "cancelled":
        next_fulfillment = "cancelled"

    update_fields = []
    if order.fulfillment_status != next_fulfillment:
        order.fulfillment_status = next_fulfillment
        update_fields.append("fulfillment_status")
    if shipment.tracking_reference and order.tracking_reference != shipment.tracking_reference:
        order.tracking_reference = shipment.tracking_reference
        update_fields.append("tracking_reference")
    if update_fields:
        update_fields.append("updated_at")
        order.save(update_fields=update_fields)
        sync_order_inventory(order, actor=actor)
    shipment.status_notes = "; ".join(delivery_blockers_for_order(order, zone=shipment.zone))
    shipment.save(update_fields=["status_notes", "updated_at"])

    if shipment.status != previous_status or shipment.tracking_reference != previous_tracking:
        record_audit_event(
            actor=actor,
            actor_label="System" if actor is None else "",
            event_type="delivery_shipment_updated",
            entity_type="delivery_shipment",
            entity_id=shipment.id,
            severity="warning" if shipment.status in {"failed", "returned", "cancelled"} else "info",
            message=f"{order.order_number} shipment moved to {shipment.status.replace('_', ' ')}.",
            meta={
                "order_number": order.order_number,
                "shipment_status": shipment.status,
                "tracking_reference": shipment.tracking_reference,
            },
        )
        _record_delivery_event(
            shipment=shipment,
            status=shipment.status,
            summary=f"Shipment manually updated to {shipment.get_status_display().lower()}.",
            actor=actor,
            meta={"tracking_reference": shipment.tracking_reference, "order_number": order.order_number},
        )
        body = f"{order.order_number} delivery is now {shipment.get_status_display().lower()}."
        if shipment.status == "failed" and shipment.next_attempt_at:
            body = (
                f"{order.order_number} delivery attempt failed. "
                f"Next attempt is planned around {timezone.localtime(shipment.next_attempt_at):%d %b %I:%M %p}."
            )
        _notify_customer_delivery_exception(
            order=order,
            title="Delivery update",
            body=body,
            shipment_status=shipment.status,
        )
        if shipment.status == "failed":
            _notify_delivery_ops(
                title="Delivery failed",
                body=f"{order.order_number} needs reattempt or return-to-origin handling.",
                meta={"order_number": order.order_number, "shipment_status": shipment.status},
            )
        if shipment.status == "queued" and previous_status == "failed" and shipment.reattempt_count > previous_reattempt_count:
            _notify_delivery_ops(
                title="Delivery reattempt scheduled",
                body=(
                    f"{order.order_number} is back in queue for reattempt "
                    f"#{shipment.reattempt_count} around {timezone.localtime(shipment.next_attempt_at):%d %b %I:%M %p}."
                ),
                meta={"order_number": order.order_number, "shipment_status": shipment.status},
            )
    return shipment


def delivery_metrics_snapshot() -> dict:
    now = timezone.now()
    queued = DeliveryShipment.objects.filter(status="queued").count()
    assigned = DeliveryShipment.objects.filter(status="assigned").count()
    in_transit = DeliveryShipment.objects.filter(status__in=["in_transit", "out_for_delivery"]).count()
    delivered = DeliveryShipment.objects.filter(status="delivered").count()
    failed = DeliveryShipment.objects.filter(status="failed").count()
    returned = DeliveryShipment.objects.filter(status="returned").count()
    reattempt_due = DeliveryShipment.objects.filter(status="failed", next_attempt_at__isnull=False, next_attempt_at__lte=now).count()
    sla_breached = DeliveryShipment.objects.filter(
        status__in=["queued", "assigned", "picked_up", "in_transit", "out_for_delivery"],
        eta_end__isnull=False,
        eta_end__lt=now,
    ).count()
    ready_queryset = DeliveryShipment.objects.select_related("order", "zone").all()
    dispatch_ready = sum(1 for shipment in ready_queryset if is_dispatch_ready(shipment.order, zone=shipment.zone) and shipment.status in {"queued", "assigned"})
    return {
        "queued_shipments": queued,
        "assigned_shipments": assigned,
        "dispatch_ready_shipments": dispatch_ready,
        "in_transit_shipments": in_transit,
        "delivered_shipments": delivered,
        "failed_shipments": failed,
        "returned_shipments": returned,
        "reattempt_due_shipments": reattempt_due,
        "sla_breached_shipments": sla_breached,
    }


def serviceability_snapshot(pincode: str) -> dict:
    ensure_delivery_zones_seeded()
    zone = find_delivery_zone_for_pincode(pincode)
    if not zone:
        return {
            "pincode": pincode,
            "is_serviceable": False,
            "cod_available": False,
            "zone": None,
            "eta_label": "",
        }
    eta_start, eta_end = estimate_delivery_window(zone=zone)
    return {
        "pincode": pincode,
        "is_serviceable": True,
        "cod_available": zone.cod_available,
        "zone": {
            "code": zone.code,
            "name": zone.name,
            "city": zone.city,
            "state": zone.state,
        },
        "eta_label": f"{zone.eta_min_hours}-{zone.eta_max_hours} hours",
        "eta_start": eta_start,
        "eta_end": eta_end,
    }
