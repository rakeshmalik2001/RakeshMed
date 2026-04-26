from decimal import Decimal
from random import randint
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from platform_apps.cart.models import Cart
from platform_apps.delivery.services import sync_delivery_for_order
from platform_apps.delivery.serializers import DeliveryShipmentSerializer
from platform_apps.inventory.services import reserve_stock_for_order

from .models import (
    Invoice,
    Order,
    OrderEvent,
    OrderItem,
    PaymentAttempt,
    PaymentWebhookEvent,
    ReconciliationSnapshot,
    RefundRequest,
    SettlementBatch,
    SettlementEntry,
)


def build_order_number():
    now = timezone.localtime()
    return f"TC-{now:%Y%m%d}-{randint(1000, 9999)}"


class OrderItemSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="product_slug")
    name = serializers.CharField(source="product_name")
    price = serializers.DecimalField(source="sale_price", max_digits=10, decimal_places=2)
    rx = serializers.BooleanField(source="requires_prescription")

    class Meta:
        model = OrderItem
        fields = ("slug", "name", "meta", "mrp", "price", "qty", "rx")


class PaymentAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = (
            "provider",
            "payment_reference",
            "status",
            "amount",
            "initiated_at",
            "confirmed_at",
        )


class OrderEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderEvent
        fields = ("event_type", "actor_name", "summary", "meta", "created_at")

    def get_actor_name(self, obj: OrderEvent) -> str:
        if obj.actor:
            return obj.actor.full_name or obj.actor.phone_number
        return obj.actor_label or "System"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payment_attempts = PaymentAttemptSerializer(many=True, read_only=True)
    delivery_shipment = DeliveryShipmentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "order_number",
            "status",
            "payment_method",
            "payment_status",
            "inventory_status",
            "fulfillment_status",
            "tracking_reference",
            "address_label",
            "recipient",
            "line1",
            "city",
            "pincode",
            "upi_id",
            "notes",
            "subtotal",
            "discount",
            "delivery_fee",
            "total",
            "requires_prescription_count",
            "created_at",
            "items",
            "payment_attempts",
            "delivery_shipment",
        )


class PaymentSessionSerializer(serializers.Serializer):
    order_number = serializers.CharField()
    payment_method = serializers.CharField()
    payment_status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    provider = serializers.CharField()
    provider_key = serializers.CharField()
    payment_reference = serializers.CharField()
    checkout_url = serializers.CharField()
    provider_order_id = serializers.CharField(required=False, allow_blank=True)
    provider_currency = serializers.CharField(required=False, allow_blank=True)


class PaymentVerificationSerializer(serializers.Serializer):
    payment_reference = serializers.CharField(required=False, allow_blank=True)
    razorpay_order_id = serializers.CharField(required=False, allow_blank=True)
    razorpay_payment_id = serializers.CharField(required=False, allow_blank=True)
    razorpay_signature = serializers.CharField(required=False, allow_blank=True)


class AdminPaymentAttemptSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    recipient = serializers.CharField(source="order.recipient", read_only=True)
    order_status = serializers.CharField(source="order.status", read_only=True)
    payment_method = serializers.CharField(source="order.payment_method", read_only=True)
    payment_status = serializers.CharField(source="order.payment_status", read_only=True)

    class Meta:
        model = PaymentAttempt
        fields = (
            "order_number",
            "recipient",
            "provider",
            "payment_reference",
            "status",
            "amount",
            "payment_method",
            "payment_status",
            "order_status",
            "initiated_at",
            "confirmed_at",
        )


class PaymentWebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentWebhookEvent
        fields = (
            "provider",
            "event_id",
            "event_type",
            "payment_reference",
            "order_number",
            "was_duplicate",
            "processed_at",
            "created_at",
        )


class ReconciliationSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationSnapshot
        fields = (
            "provider",
            "captured_total",
            "refunded_total",
            "pending_refund_count",
            "duplicate_webhooks",
            "processed_webhooks",
            "unmatched_paid_orders",
            "created_by_label",
            "notes",
            "created_at",
        )


class SettlementEntrySerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    payment_reference = serializers.CharField(source="payment_attempt.payment_reference", read_only=True)
    refund_status = serializers.SerializerMethodField()

    class Meta:
        model = SettlementEntry
        fields = (
            "order_number",
            "payment_reference",
            "gross_amount",
            "refund_amount",
            "net_amount",
            "settlement_status",
            "refund_status",
            "created_at",
        )

    def get_refund_status(self, obj: SettlementEntry) -> str:
        return obj.refund_request.status if obj.refund_request else ""


class SettlementBatchSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    entries = SettlementEntrySerializer(many=True, read_only=True)

    class Meta:
        model = SettlementBatch
        fields = (
            "id",
            "provider",
            "batch_reference",
            "period_start",
            "period_end",
            "total_captured",
            "total_refunded",
            "total_net",
            "status",
            "created_by_name",
            "notes",
            "created_at",
            "entries",
        )

    def get_created_by_name(self, obj: SettlementBatch) -> str:
        if not obj.created_by:
            return ""
        return obj.created_by.full_name or obj.created_by.phone_number


class SettlementBatchCreateSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True)
    period_start = serializers.DateTimeField(required=False)
    period_end = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class SettlementBatchUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["draft", "processing", "closed"], required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class RefundRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = (
            "id",
            "reason",
            "status",
            "amount",
            "resolution_notes",
            "requested_by_name",
            "created_at",
            "updated_at",
            "processed_at",
        )

    def get_requested_by_name(self, obj: RefundRequest) -> str:
        if obj.requested_by:
            return obj.requested_by.full_name or obj.requested_by.phone_number
        return "System"


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "invoice_number",
            "status",
            "recipient",
            "line1",
            "city",
            "pincode",
            "subtotal",
            "discount",
            "delivery_fee",
            "tax_amount",
            "total",
            "snapshot",
            "issued_at",
        )


class OrderDetailSerializer(OrderSerializer):
    timeline = OrderEventSerializer(many=True, read_only=True)
    refund_requests = RefundRequestSerializer(many=True, read_only=True)
    invoice = InvoiceSerializer(read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ("timeline", "refund_requests", "invoice")


class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("status", "payment_status", "fulfillment_status", "tracking_reference", "notes")


class CheckoutAddressSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    recipient = serializers.CharField(max_length=255)
    line1 = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=120)
    pincode = serializers.CharField(max_length=20)


class CheckoutSerializer(serializers.Serializer):
    address = CheckoutAddressSerializer()
    payment_method = serializers.ChoiceField(choices=["UPI", "CARD", "COD", "WALLET"])
    upi_id = serializers.CharField(max_length=120, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["payment_method"] == "UPI" and not attrs.get("upi_id"):
            raise serializers.ValidationError({"upi_id": "UPI ID is required for UPI payments."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        cart, _ = Cart.objects.get_or_create(user=user)
        items = list(cart.items.all())

        if not items:
            raise serializers.ValidationError({"detail": "Your cart is empty."})

        subtotal = sum(Decimal(item.mrp) * item.qty for item in items)
        discounted = sum(Decimal(item.sale_price) * item.qty for item in items)
        delivery_fee = Decimal("40.00") if items else Decimal("0.00")
        discount = subtotal - discounted
        requires_prescription_count = sum(item.qty for item in items if item.requires_prescription)
        address = validated_data["address"]
        payment_method = validated_data["payment_method"]

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                order_number=build_order_number(),
                status="pending_prescription_review" if requires_prescription_count else "placed",
                payment_method=payment_method,
                payment_status="cod_pending" if payment_method == "COD" else "pending",
                address_label=address.get("label", ""),
                recipient=address["recipient"],
                line1=address["line1"],
                city=address["city"],
                pincode=address["pincode"],
                upi_id=validated_data.get("upi_id", ""),
                notes=validated_data.get("notes", ""),
                subtotal=subtotal,
                discount=discount,
                delivery_fee=delivery_fee,
                total=discounted + delivery_fee,
                requires_prescription_count=requires_prescription_count,
            )

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=item.product,
                        product_slug=item.product_slug,
                        product_name=item.name,
                        meta=item.meta,
                        mrp=item.mrp,
                        sale_price=item.sale_price,
                        qty=item.qty,
                        requires_prescription=item.requires_prescription,
                    )
                    for item in items
                ]
            )
            reserve_stock_for_order(order, actor=user, reason="checkout")
            sync_delivery_for_order(order, actor=user, notes="Order entered delivery queue.")
            cart.items.all().delete()
        return order


class RefundRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


class RefundRequestDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = ("status", "resolution_notes")
