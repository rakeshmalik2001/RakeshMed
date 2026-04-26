from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from platform_apps.catalog.models import Product

from .models import InventoryItem, StockLocation, StockMovement


def get_default_location() -> StockLocation:
    location, _created = StockLocation.objects.get_or_create(
        code="MAIN",
        defaults={
            "name": "Main Warehouse",
            "kind": "warehouse",
            "sort_order": 0,
            "is_active": True,
        },
    )
    return location


def _notify_ops_users(*, kind: str, title: str, body: str, link: str = "", meta: dict | None = None) -> None:
    from platform_apps.notifications.models import Notification
    from platform_apps.notifications.services import create_notification
    from platform_apps.users.models import User

    meta = meta or {}
    alert_key = meta.get("alert_key")
    recipients = User.objects.filter(
        is_active=True,
        role__in=["admin", "warehouse_operator", "catalog_manager", "support_agent", "finance"],
    )
    for user in recipients.iterator():
        if alert_key and Notification.objects.filter(
            user=user,
            kind=kind,
            is_read=False,
            meta__alert_key=alert_key,
        ).exists():
            continue
        create_notification(user=user, kind=kind, title=title, body=body, link=link, meta=meta)


def _resolve_inventory_alerts(*, product: Product) -> None:
    from platform_apps.notifications.models import Notification

    Notification.objects.filter(
        kind="inventory_alert",
        is_read=False,
        meta__product_id=product.id,
    ).update(is_read=True, read_at=timezone.now())


def _notify_inventory_status_change(*, product: Product, previous_status: str, next_status: str) -> None:
    if next_status == "in_stock":
        _resolve_inventory_alerts(product=product)
        _notify_ops_users(
            kind="inventory_alert",
            title=f"{product.name} back in stock",
            body=f"{product.name} recovered from {previous_status.replace('_', ' ')} to in stock.",
            link="/admin/inventory/inventoryitem/",
            meta={"product_id": product.id, "alert_key": f"inventory:{product.id}:recovered", "stock_status": next_status},
        )
        return

    alert_copy = {
        "low_stock": (
            "Low stock warning",
            f"{product.name} crossed its replenishment threshold and needs attention.",
        ),
        "out_of_stock": (
            "Out of stock alert",
            f"{product.name} is no longer available for new orders without restocking.",
        ),
    }
    title, body = alert_copy.get(next_status, ("Inventory alert", f"{product.name} changed to {next_status}."))
    _notify_ops_users(
        kind="inventory_alert",
        title=title,
        body=body,
        link="/admin/inventory/inventoryitem/",
        meta={"product_id": product.id, "alert_key": f"inventory:{product.id}:{next_status}", "stock_status": next_status},
    )


def get_product_low_stock_threshold(product: Product) -> int:
    if hasattr(product, "low_stock_rule"):
        return product.low_stock_rule.threshold_quantity
    return 5


def refresh_product_stock_status(product: Product) -> Product:
    aggregates = product.inventory_items.filter(location__is_active=True).aggregate(
        total_on_hand=Sum("quantity_on_hand"),
        total_reserved=Sum("reserved_quantity"),
    )
    total_on_hand = aggregates.get("total_on_hand") or 0
    total_reserved = aggregates.get("total_reserved") or 0
    total_available = total_on_hand - total_reserved
    threshold = get_product_low_stock_threshold(product)

    if total_available <= 0:
        next_status = "out_of_stock"
    elif total_available <= threshold:
        next_status = "low_stock"
    else:
        next_status = "in_stock"

    if product.stock_status != next_status:
        previous_status = product.stock_status
        product.stock_status = next_status
        product.save(update_fields=["stock_status", "updated_at"])
        _notify_inventory_status_change(product=product, previous_status=previous_status, next_status=next_status)

    return product


def ensure_product_inventory(product: Product) -> InventoryItem:
    return InventoryItem.objects.get_or_create(
        product=product,
        location=get_default_location(),
        defaults={"quantity_on_hand": 0, "reserved_quantity": 0, "inbound_quantity": 0},
    )[0]


def _active_inventory_items_for_product(product: Product) -> list[InventoryItem]:
    inventory_items = list(
        product.inventory_items.select_related("location")
        .filter(location__is_active=True)
        .select_for_update()
        .order_by("location__sort_order", "location__name", "id")
    )
    if inventory_items:
        return inventory_items
    ensure_product_inventory(product)
    return list(
        product.inventory_items.select_related("location")
        .filter(location__is_active=True)
        .select_for_update()
        .order_by("location__sort_order", "location__name", "id")
    )


def _set_order_inventory_status(order, status: str) -> None:
    if order.inventory_status != status:
        order.inventory_status = status
        order.save(update_fields=["inventory_status", "updated_at"])


def _movement_reference(order, suffix: str) -> str:
    return f"{order.order_number}:{suffix}"


def reserve_stock_for_order(order, *, actor=None, reason: str = ""):
    if order.inventory_status == "reserved":
        return order
    if order.inventory_status == "completed":
        return order

    with transaction.atomic():
        for order_item in order.items.select_related("product").order_by("id"):
            if not order_item.product_id:
                continue
            product = order_item.product
            inventory_items = _active_inventory_items_for_product(product)
            total_available = sum(max(item.available_quantity, 0) for item in inventory_items)
            if total_available < order_item.qty:
                _notify_ops_users(
                    kind="inventory_alert",
                    title="Order blocked by stock shortage",
                    body=(
                        f"{order.order_number} could not reserve {order_item.qty} unit(s) of {product.name}. "
                        f"Only {total_available} available."
                    ),
                    link=f"/admin/orders/order/",
                    meta={
                        "product_id": product.id,
                        "order_number": order.order_number,
                        "alert_key": f"shortage:{order.order_number}:{product.id}",
                    },
                )
                raise ValidationError(f"Insufficient stock for {product.name}. Only {total_available} unit(s) available.")

            remaining = order_item.qty
            for inventory_item in inventory_items:
                allocatable = min(max(inventory_item.available_quantity, 0), remaining)
                if allocatable <= 0:
                    continue
                inventory_item.reserved_quantity += allocatable
                inventory_item.save(update_fields=["reserved_quantity", "updated_at"])
                StockMovement.objects.create(
                    product=product,
                    inventory_item=inventory_item,
                    location=inventory_item.location,
                    movement_type="sale_allocation",
                    quantity_delta=0,
                    reference=_movement_reference(order, "reserve"),
                    notes=reason or "Reserved stock for order lifecycle.",
                    created_by=actor,
                )
                remaining -= allocatable
                if remaining == 0:
                    break
            refresh_product_stock_status(product)

        _set_order_inventory_status(order, "reserved")
    return order


def release_stock_for_order(order, *, actor=None, reason: str = ""):
    if order.inventory_status not in {"reserved", "released"}:
        return order
    if order.inventory_status == "released":
        return order

    with transaction.atomic():
        for order_item in order.items.select_related("product").order_by("id"):
            if not order_item.product_id:
                continue
            product = order_item.product
            inventory_items = _active_inventory_items_for_product(product)
            remaining = order_item.qty
            total_reserved = sum(item.reserved_quantity for item in inventory_items)
            if total_reserved < remaining:
                raise ValidationError(f"Reserved stock mismatch for {product.name}.")

            for inventory_item in inventory_items:
                releasable = min(inventory_item.reserved_quantity, remaining)
                if releasable <= 0:
                    continue
                inventory_item.reserved_quantity -= releasable
                inventory_item.save(update_fields=["reserved_quantity", "updated_at"])
                StockMovement.objects.create(
                    product=product,
                    inventory_item=inventory_item,
                    location=inventory_item.location,
                    movement_type="sale_release",
                    quantity_delta=0,
                    reference=_movement_reference(order, "release"),
                    notes=reason or "Released reserved stock back to availability.",
                    created_by=actor,
                )
                remaining -= releasable
                if remaining == 0:
                    break
            refresh_product_stock_status(product)

        _set_order_inventory_status(order, "released")
    return order


def complete_stock_for_order(order, *, actor=None, reason: str = ""):
    if order.inventory_status == "completed":
        return order

    with transaction.atomic():
        if order.inventory_status in {"unreserved", "released", "returned"}:
            reserve_stock_for_order(order, actor=actor, reason="Auto-reserved before completion")
            order.refresh_from_db(fields=["inventory_status", "updated_at"])

        if order.inventory_status != "reserved":
            return order

        for order_item in order.items.select_related("product").order_by("id"):
            if not order_item.product_id:
                continue
            product = order_item.product
            inventory_items = _active_inventory_items_for_product(product)
            remaining = order_item.qty
            total_reserved = sum(item.reserved_quantity for item in inventory_items)
            if total_reserved < remaining:
                raise ValidationError(f"Reserved stock mismatch for {product.name}.")

            for inventory_item in inventory_items:
                consumable = min(inventory_item.reserved_quantity, remaining)
                if consumable <= 0:
                    continue
                inventory_item.reserved_quantity -= consumable
                inventory_item.quantity_on_hand -= consumable
                inventory_item.save(update_fields=["reserved_quantity", "quantity_on_hand", "updated_at"])
                StockMovement.objects.create(
                    product=product,
                    inventory_item=inventory_item,
                    location=inventory_item.location,
                    movement_type="sale_complete",
                    quantity_delta=-consumable,
                    reference=_movement_reference(order, "complete"),
                    notes=reason or "Committed reserved stock to completed sale.",
                    created_by=actor,
                )
                remaining -= consumable
                if remaining == 0:
                    break
            refresh_product_stock_status(product)

        _set_order_inventory_status(order, "completed")
    return order


def return_stock_for_order(order, *, actor=None, reason: str = ""):
    if order.inventory_status == "returned":
        return order

    with transaction.atomic():
        if order.inventory_status == "reserved":
            return release_stock_for_order(order, actor=actor, reason=reason or "Returned to available pool before sale completion.")

        if order.inventory_status != "completed":
            return order

        default_location = get_default_location()
        for order_item in order.items.select_related("product").order_by("id"):
            if not order_item.product_id:
                continue
            product = order_item.product
            inventory_item, _created = InventoryItem.objects.select_for_update().get_or_create(
                product=product,
                location=default_location,
                defaults={"quantity_on_hand": 0, "reserved_quantity": 0, "inbound_quantity": 0},
            )
            inventory_item.quantity_on_hand += order_item.qty
            inventory_item.save(update_fields=["quantity_on_hand", "updated_at"])
            StockMovement.objects.create(
                product=product,
                inventory_item=inventory_item,
                location=inventory_item.location,
                movement_type="return",
                quantity_delta=order_item.qty,
                reference=_movement_reference(order, "return"),
                notes=reason or "Returned stock back to inventory.",
                created_by=actor,
            )
            refresh_product_stock_status(product)

        _set_order_inventory_status(order, "returned")
    return order


def sync_order_inventory(order, *, actor=None, actor_label: str = ""):
    del actor_label
    if order.payment_status == "refunded":
        return return_stock_for_order(order, actor=actor, reason="Refund completed")

    if order.fulfillment_status == "returned":
        return return_stock_for_order(order, actor=actor, reason="Shipment returned")

    if order.fulfillment_status == "cancelled":
        if order.inventory_status == "completed":
            return return_stock_for_order(order, actor=actor, reason="Shipment cancelled after stock completion")
        return release_stock_for_order(order, actor=actor, reason="Shipment cancelled before dispatch")

    if order.status == "cancelled" or order.payment_status == "failed":
        if order.inventory_status == "completed":
            return return_stock_for_order(order, actor=actor, reason="Order cancelled or payment failed after completion")
        return release_stock_for_order(order, actor=actor, reason="Order cancelled or payment failed")

    if order.fulfillment_status in {"shipped", "delivered"}:
        return complete_stock_for_order(order, actor=actor, reason="Order moved into shipment or delivery")

    return reserve_stock_for_order(order, actor=actor, reason="Order entered active lifecycle")


def inventory_risk_snapshot(*, limit: int = 5) -> dict:
    low_stock_products = list(
        Product.objects.filter(is_active=True, stock_status="low_stock").order_by("name")[:limit]
    )
    out_of_stock_products = list(
        Product.objects.filter(is_active=True, stock_status="out_of_stock").order_by("name")[:limit]
    )
    return {
        "low_stock_count": Product.objects.filter(is_active=True, stock_status="low_stock").count(),
        "out_of_stock_count": Product.objects.filter(is_active=True, stock_status="out_of_stock").count(),
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
    }
