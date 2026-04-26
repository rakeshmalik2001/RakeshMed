from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils.html import escape
from rest_framework.exceptions import PermissionDenied

from platform_apps.delivery.services import sync_delivery_for_order
from platform_apps.inventory.services import sync_order_inventory
from platform_apps.notifications.services import create_notification

from .adapters import NormalizedPaymentEvent, get_payment_adapter
from .models import Invoice, Order, OrderEvent, PaymentWebhookEvent, ReconciliationSnapshot


def record_order_event(
    *,
    order: Order,
    event_type: str,
    summary: str,
    actor=None,
    actor_label: str = "",
    meta: dict | None = None,
) -> OrderEvent:
    resolved_actor_label = actor_label or (getattr(actor, "full_name", "") or getattr(actor, "phone_number", ""))
    return OrderEvent.objects.create(
        order=order,
        event_type=event_type,
        actor=actor,
        actor_label=resolved_actor_label,
        summary=summary,
        meta=meta or {},
    )


def create_order_notification(
    *,
    order: Order,
    kind: str,
    title: str,
    body: str,
    link: str | None = None,
    meta: dict | None = None,
):
    return create_notification(
        user=order.user,
        kind=kind,
        title=title,
        body=body,
        link=link or f"/account/orders/{order.order_number}",
        meta={"order_number": order.order_number, **(meta or {})},
    )


def sync_inventory_for_order(
    *,
    order: Order,
    actor=None,
    actor_label: str = "",
):
    return sync_order_inventory(order, actor=actor, actor_label=actor_label)


def sync_delivery_for_order_lifecycle(
    *,
    order: Order,
    actor=None,
    notes: str = "",
):
    return sync_delivery_for_order(order, actor=actor, notes=notes)


def verify_payment_webhook(request) -> None:
    provider = str(request.data.get("provider", "")).strip() or None
    get_payment_adapter(provider).validate_webhook(request)


def extract_webhook_signature(request) -> str:
    return request.headers.get("X-Razorpay-Signature", "").strip() or request.headers.get("X-Webhook-Secret", "").strip()


def create_payment_session_payload(*, order: Order, reference: str) -> dict:
    from .models import PaymentAttempt

    attempt = PaymentAttempt.objects.get(payment_reference=reference)
    return get_payment_adapter(attempt.provider).create_payment_session(order=order, attempt=attempt)


def register_webhook_event(request) -> tuple[PaymentWebhookEvent, bool]:
    normalized_event = parse_payment_webhook(request)
    event_id = normalized_event.event_id
    if not event_id:
        raise PermissionDenied("Missing webhook event id.")

    webhook_event, created = PaymentWebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "provider": normalized_event.provider,
            "event_type": normalized_event.provider_event_type,
            "payment_reference": normalized_event.payment_reference,
            "order_number": normalized_event.order_number,
            "signature": extract_webhook_signature(request),
            "payload": normalized_event.raw_payload,
        },
    )
    if not created:
        webhook_event.was_duplicate = True
        webhook_event.signature = extract_webhook_signature(request)
        webhook_event.payload = normalized_event.raw_payload
        webhook_event.save(update_fields=["was_duplicate", "signature", "payload"])
        return webhook_event, True
    return webhook_event, False


def mark_webhook_processed(webhook_event: PaymentWebhookEvent, *, event_type: str) -> None:
    from django.utils import timezone

    webhook_event.event_type = event_type
    webhook_event.processed_at = timezone.now()
    webhook_event.save(update_fields=["event_type", "processed_at"])


def parse_payment_webhook(request) -> NormalizedPaymentEvent:
    provider = str(request.data.get("provider", "")).strip() or None
    return get_payment_adapter(provider).parse_webhook(request)


def build_reconciliation_snapshot(*, created_by_label: str = "", notes: str = "") -> ReconciliationSnapshot:
    from .models import PaymentAttempt, RefundRequest

    attempts = PaymentAttempt.objects.all()
    refunds = RefundRequest.objects.all()
    webhooks = PaymentWebhookEvent.objects.all()

    return ReconciliationSnapshot.objects.create(
        provider=get_payment_adapter().provider_name,
        captured_total=attempts.filter(status="captured").aggregate(total=Sum("amount"))["total"] or 0,
        refunded_total=refunds.filter(status="processed").aggregate(total=Sum("amount"))["total"] or 0,
        pending_refund_count=refunds.filter(status__in=["requested", "approved"]).count(),
        duplicate_webhooks=webhooks.filter(was_duplicate=True).count(),
        processed_webhooks=webhooks.filter(processed_at__isnull=False).count(),
        unmatched_paid_orders=Order.objects.filter(payment_status="paid").exclude(
            payment_attempts__status__in=["captured", "refunded"]
        ).count(),
        created_by_label=created_by_label,
        notes=notes,
    )


def build_invoice_snapshot(order: Order) -> dict:
    return {
        "order_number": order.order_number,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "items": [
            {
                "name": item.product_name,
                "slug": item.product_slug,
                "qty": item.qty,
                "mrp": str(item.mrp),
                "sale_price": str(item.sale_price),
                "line_total": str(Decimal(item.sale_price) * item.qty),
                "requires_prescription": item.requires_prescription,
            }
            for item in order.items.all()
        ],
    }


def issue_invoice_for_order(order: Order) -> Invoice | None:
    if order.payment_status != "paid":
        return None

    existing = getattr(order, "invoice", None)
    if existing:
        snapshot = build_invoice_snapshot(order)
        refresh_fields = []
        if existing.snapshot != snapshot:
            existing.snapshot = snapshot
            refresh_fields.append("snapshot")
        if existing.total != order.total:
            existing.total = order.total
            existing.subtotal = order.subtotal
            existing.discount = order.discount
            existing.delivery_fee = order.delivery_fee
            refresh_fields.extend(["total", "subtotal", "discount", "delivery_fee"])
        if refresh_fields:
            existing.save(update_fields=[*refresh_fields, "updated_at"])
        return existing

    return Invoice.objects.create(
        order=order,
        invoice_number=f"INV-{order.created_at:%Y%m%d}-{order.pk:06d}",
        status="issued",
        recipient=order.recipient,
        line1=order.line1,
        city=order.city,
        pincode=order.pincode,
        subtotal=order.subtotal,
        discount=order.discount,
        delivery_fee=order.delivery_fee,
        tax_amount=Decimal("0.00"),
        total=order.total,
        snapshot=build_invoice_snapshot(order),
    )


def render_invoice_html(invoice: Invoice) -> str:
    items = invoice.snapshot.get("items", [])
    item_rows = "".join(
        (
            "<tr>"
            f"<td>{escape(item.get('name', ''))}</td>"
            f"<td>{escape(str(item.get('qty', '')))}</td>"
            f"<td>Rs. {escape(str(item.get('sale_price', '0.00')))}</td>"
            f"<td>Rs. {escape(str(item.get('line_total', '0.00')))}</td>"
            "</tr>"
        )
        for item in items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{escape(invoice.invoice_number)}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; color: #15202b; }}
      h1, h2, p {{ margin: 0; }}
      .header, .summary {{ display: flex; justify-content: space-between; gap: 24px; margin-bottom: 24px; }}
      .card {{ border: 1px solid #d7e1ea; border-radius: 12px; padding: 16px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
      th, td {{ border-bottom: 1px solid #e7edf3; padding: 12px 8px; text-align: left; }}
      .totals {{ margin-top: 24px; width: 320px; margin-left: auto; }}
      .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; }}
    </style>
  </head>
  <body>
    <div class="header">
      <div>
        <h1>{escape(settings.COMPLIANCE_COMPANY_NAME)}</h1>
        <p>{escape(settings.COMPLIANCE_SUPPORT_EMAIL)}</p>
        <p>Drug License: {escape(settings.COMPLIANCE_DRUG_LICENSE_NUMBER)}</p>
      </div>
      <div class="card">
        <h2>Tax Invoice</h2>
        <p>Invoice: {escape(invoice.invoice_number)}</p>
        <p>Order: {escape(invoice.order.order_number)}</p>
        <p>Issued: {escape(invoice.issued_at.strftime("%d %b %Y, %I:%M %p"))}</p>
      </div>
    </div>
    <div class="summary">
      <div class="card">
        <h2>Bill To</h2>
        <p>{escape(invoice.recipient)}</p>
        <p>{escape(invoice.line1)}</p>
        <p>{escape(invoice.city)} - {escape(invoice.pincode)}</p>
      </div>
      <div class="card">
        <h2>Payment</h2>
        <p>Method: {escape(invoice.order.payment_method)}</p>
        <p>Status: {escape(invoice.order.payment_status.replace('_', ' '))}</p>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Item</th>
          <th>Qty</th>
          <th>Unit Price</th>
          <th>Line Total</th>
        </tr>
      </thead>
      <tbody>{item_rows}</tbody>
    </table>
    <div class="totals">
      <div><span>Subtotal</span><strong>Rs. {invoice.subtotal}</strong></div>
      <div><span>Discount</span><strong>- Rs. {invoice.discount}</strong></div>
      <div><span>Delivery Fee</span><strong>Rs. {invoice.delivery_fee}</strong></div>
      <div><span>Tax</span><strong>Rs. {invoice.tax_amount}</strong></div>
      <div><span>Total</span><strong>Rs. {invoice.total}</strong></div>
    </div>
  </body>
</html>"""
