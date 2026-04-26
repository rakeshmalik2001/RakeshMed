from django.db import migrations
from django.utils import timezone


def _find_zone(DeliveryZone, pincode: str):
    normalized = "".join(ch for ch in str(pincode) if ch.isdigit())
    for length in range(min(6, len(normalized)), 0, -1):
        zone = DeliveryZone.objects.filter(is_active=True, pincode_prefix=normalized[:length]).first()
        if zone:
            return zone
    return None


def backfill_shipments(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    DeliveryZone = apps.get_model("delivery", "DeliveryZone")
    DeliveryShipment = apps.get_model("delivery", "DeliveryShipment")
    DeliveryEvent = apps.get_model("delivery", "DeliveryEvent")

    for order in Order.objects.all().iterator():
        if DeliveryShipment.objects.filter(order_id=order.id).exists():
            continue
        zone = _find_zone(DeliveryZone, order.pincode)
        if order.fulfillment_status in {"queued"}:
            shipment_status = "queued"
        elif order.fulfillment_status in {"packed"}:
            shipment_status = "assigned"
        elif order.fulfillment_status in {"shipped"}:
            shipment_status = "in_transit"
        elif order.fulfillment_status == "delivered":
            shipment_status = "delivered"
        elif order.fulfillment_status == "returned":
            shipment_status = "returned"
        elif order.fulfillment_status == "cancelled":
            shipment_status = "cancelled"
        else:
            shipment_status = "queued"

        eta_start = order.created_at + timezone.timedelta(hours=getattr(zone, "eta_min_hours", 24))
        eta_end = order.created_at + timezone.timedelta(hours=getattr(zone, "eta_max_hours", 48))
        shipment = DeliveryShipment.objects.create(
            order_id=order.id,
            zone_id=getattr(zone, "id", None),
            carrier_name="TrueCare Dispatch",
            service_level="standard",
            status=shipment_status,
            tracking_reference=order.tracking_reference,
            status_notes="Backfilled from existing order lifecycle.",
            eta_start=eta_start,
            eta_end=eta_end,
        )
        DeliveryEvent.objects.create(
            shipment_id=shipment.id,
            status=shipment.status,
            summary="Shipment backfilled from existing order lifecycle.",
            meta={"order_number": order.order_number},
        )


def rollback_shipments(apps, schema_editor):
    DeliveryShipment = apps.get_model("delivery", "DeliveryShipment")
    DeliveryShipment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_shipments, rollback_shipments),
    ]
