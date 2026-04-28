from decimal import Decimal

from django.conf import settings
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    abort_idempotent_request,
    attach_idempotency_headers,
    begin_idempotent_request,
    complete_idempotent_request,
)
from platform_apps.audit.services import record_audit_event
from config.throttles import CheckoutThrottle, PaymentSessionThrottle, PaymentWebhookThrottle
from platform_apps.catalog.models import Product
from platform_apps.prescriptions.models import Prescription
from platform_apps.users.models import CustomerAddress, SavedPaymentMethod, User
from platform_apps.users.views import HasMatrixPermission

from .models import (
    Order,
    PaymentAttempt,
    PaymentWebhookEvent,
    ReconciliationSnapshot,
    RefundRequest,
    SettlementBatch,
    SettlementEntry,
)
from .serializers import (
    AdminOrderUpdateSerializer,
    AdminPaymentAttemptSerializer,
    CheckoutSerializer,
    RefundRequestCreateSerializer,
    RefundRequestDecisionSerializer,
    OrderDetailSerializer,
    OrderSerializer,
    PaymentWebhookEventSerializer,
    ReconciliationSnapshotSerializer,
    PaymentSessionSerializer,
    PaymentVerificationSerializer,
    SettlementBatchCreateSerializer,
    SettlementBatchSerializer,
    SettlementBatchUpdateSerializer,
)
from .services import (
    build_reconciliation_snapshot,
    create_order_notification,
    create_payment_session_payload,
    issue_invoice_for_order,
    mark_webhook_processed,
    parse_payment_webhook,
    record_order_event,
    register_webhook_event,
    render_invoice_html,
    sync_delivery_for_order_lifecycle,
    sync_inventory_for_order,
    verify_payment_webhook,
)
from .adapters import get_payment_adapter


class IsAdminOrOps(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in {"admin", "catalog_manager", "finance", "support_agent", "warehouse_operator"})
        )


class OrderCheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "orders.create_order"
    throttle_classes = [CheckoutThrottle]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            idempotency_cache_key, replay = begin_idempotent_request(request=request, namespace="order-checkout")
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IdempotencyInProgress as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        if replay:
            order = generics.get_object_or_404(
                Order.objects.filter(user=request.user)
                .prefetch_related("items", "payment_attempts", "timeline", "refund_requests"),
                order_number=replay.value["order_number"],
            )
            response = Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)
            attach_idempotency_headers(response, replayed=True)
            return response

        try:
            order = serializer.save()
        except Exception:
            abort_idempotent_request(cache_key=idempotency_cache_key)
            raise
        record_order_event(
            order=order,
            event_type="placed",
            summary=f"Order placed for Rs. {order.total} via {order.payment_method}.",
            actor=request.user,
            meta={"payment_method": order.payment_method, "payment_status": order.payment_status},
        )
        create_order_notification(
            order=order,
            kind="order_update",
            title="Order placed successfully",
            body=f"{order.order_number} is now {order.status.replace('_', ' ')}.",
            meta={"payment_status": order.payment_status},
        )
        complete_idempotent_request(
            cache_key=idempotency_cache_key,
            request=request,
            value={"order_number": order.order_number},
        )
        response = Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)
        attach_idempotency_headers(response, replayed=False)
        return response


class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "orders.view_orders"
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("delivery_shipment", "delivery_shipment__zone").prefetch_related("items", "delivery_shipment__events", "delivery_shipment__events__created_by")


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "orders.view_orders"
    serializer_class = OrderDetailSerializer
    lookup_field = "order_number"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("delivery_shipment", "delivery_shipment__zone", "invoice").prefetch_related("items", "payment_attempts", "timeline", "refund_requests", "delivery_shipment__events", "delivery_shipment__events__created_by")


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "orders.cancel_order"

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order.objects.filter(user=request.user), order_number=order_number)

        if order.status == "cancelled":
            return Response(OrderSerializer(order).data)

        if order.status not in {"placed", "pending_prescription_review", "confirmed"}:
            return Response({"detail": "This order cannot be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        order.status = "cancelled"
        order.fulfillment_status = "cancelled"
        if order.payment_method == "COD":
            order.payment_status = "failed"
        order.save(update_fields=["status", "fulfillment_status", "payment_status", "updated_at"])
        sync_inventory_for_order(order=order, actor=request.user)
        sync_delivery_for_order_lifecycle(order=order, actor=request.user, notes="Customer cancelled order before delivery.")
        record_order_event(
            order=order,
            event_type="cancelled",
            summary="Customer cancelled the order before fulfillment.",
            actor=request.user,
            meta={"payment_status": order.payment_status},
        )
        create_order_notification(
            order=order,
            kind="order_update",
            title="Order cancelled",
            body=f"{order.order_number} has been cancelled.",
            meta={"payment_status": order.payment_status},
        )
        return Response(OrderDetailSerializer(order).data)


class OrderPaymentConfirmView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "finance.make_payment"

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order.objects.filter(user=request.user), order_number=order_number)

        if order.payment_method == "COD":
            return Response({"detail": "Cash on Delivery orders are paid at delivery."}, status=status.HTTP_400_BAD_REQUEST)

        if order.status == "cancelled":
            return Response({"detail": "Cancelled orders cannot be paid."}, status=status.HTTP_400_BAD_REQUEST)

        latest_attempt = order.payment_attempts.order_by("-initiated_at").first()
        if latest_attempt and latest_attempt.provider == "razorpay":
            return Response(
                {"detail": "Razorpay orders must be updated through gateway verification or webhooks."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if latest_attempt:
            latest_attempt.status = "captured"
            latest_attempt.confirmed_at = timezone.now()
            latest_attempt.save(update_fields=["status", "confirmed_at"])

        order.payment_status = "paid"
        if order.status == "placed":
            order.status = "confirmed"
        order.save(update_fields=["payment_status", "status", "updated_at"])
        invoice = issue_invoice_for_order(order)
        sync_inventory_for_order(order=order, actor=request.user)
        sync_delivery_for_order_lifecycle(order=order, actor=request.user, notes="Payment confirmed and order ready for fulfillment queue.")
        record_order_event(
            order=order,
            event_type="payment_captured",
            summary=f"Customer confirmed payment for {order.order_number}.",
            actor=request.user,
            meta={
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "invoice_number": invoice.invoice_number if invoice else "",
            },
        )
        create_order_notification(
            order=order,
            kind="payment_update",
            title="Payment received",
            body=f"Payment for {order.order_number} is now marked paid.",
            meta={"payment_method": order.payment_method},
        )
        order = Order.objects.filter(pk=order.pk).select_related("invoice", "delivery_shipment", "delivery_shipment__zone").prefetch_related("items", "payment_attempts", "timeline", "refund_requests", "delivery_shipment__events", "delivery_shipment__events__created_by").get()
        return Response(OrderDetailSerializer(order).data)


class OrderPaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "finance.make_payment"

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order.objects.filter(user=request.user), order_number=order_number)
        serializer = PaymentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_reference = serializer.validated_data.get("payment_reference", "").strip()
        if payment_reference:
            attempt = generics.get_object_or_404(
                order.payment_attempts.all(),
                payment_reference=payment_reference,
            )
        else:
            attempt = order.payment_attempts.order_by("-initiated_at").first()
            if not attempt:
                return Response({"detail": "No payment attempt found for this order."}, status=status.HTTP_404_NOT_FOUND)

        verification = get_payment_adapter(attempt.provider).verify_client_payment(
            order=order,
            attempt=attempt,
            payload=serializer.validated_data,
        )

        attempt.status = "captured" if verification.normalized_status in {"captured", "paid", "success"} else verification.normalized_status
        attempt.confirmed_at = timezone.now()
        attempt.raw_payload = verification.raw_payload
        attempt.save(update_fields=["status", "confirmed_at", "raw_payload"])

        order.payment_status = "paid"
        if order.status == "placed":
            order.status = "confirmed"
        order.save(update_fields=["payment_status", "status", "updated_at"])
        invoice = issue_invoice_for_order(order)
        sync_inventory_for_order(order=order, actor=request.user)
        sync_delivery_for_order_lifecycle(order=order, actor=request.user, notes="Customer completed Razorpay checkout.")
        record_order_event(
            order=order,
            event_type="payment_captured",
            summary=f"Verified gateway payment for {attempt.payment_reference}.",
            actor=request.user,
            meta={
                "provider": attempt.provider,
                "provider_payment_id": verification.provider_payment_id,
                "invoice_number": invoice.invoice_number if invoice else "",
            },
        )
        create_order_notification(
            order=order,
            kind="payment_update",
            title="Payment received",
            body=f"{order.order_number} payment was verified successfully.",
            meta={"payment_reference": attempt.payment_reference, "provider_payment_id": verification.provider_payment_id},
        )
        refreshed = Order.objects.filter(pk=order.pk).select_related(
            "invoice",
            "delivery_shipment",
            "delivery_shipment__zone",
        ).prefetch_related(
            "items",
            "payment_attempts",
            "timeline",
            "refund_requests",
            "delivery_shipment__events",
            "delivery_shipment__events__created_by",
        ).get()
        return Response(OrderDetailSerializer(refreshed).data)


class OrderInvoiceDownloadView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "orders.view_orders"

    def get(self, request, order_number):
        order = generics.get_object_or_404(
            Order.objects.filter(user=request.user).select_related("invoice"),
            order_number=order_number,
        )
        invoice = getattr(order, "invoice", None)
        if not invoice:
            return Response({"detail": "Invoice is not available for this order yet."}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(render_invoice_html(invoice), content_type="text/html; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{invoice.invoice_number}.html"'
        return response


class OrderPaymentSessionView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "finance.make_payment"
    throttle_classes = [PaymentSessionThrottle]

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order.objects.filter(user=request.user), order_number=order_number)

        if order.payment_method == "COD":
            return Response({"detail": "Cash on Delivery orders do not need an online payment session."}, status=status.HTTP_400_BAD_REQUEST)

        if order.status == "cancelled":
            return Response({"detail": "Cancelled orders cannot start a payment session."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idempotency_cache_key, replay = begin_idempotent_request(request=request, namespace="payment-session")
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IdempotencyInProgress as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        if replay:
            attempt = generics.get_object_or_404(
                PaymentAttempt.objects.select_related("order").filter(order__user=request.user),
                payment_reference=replay.value["payment_reference"],
            )
            payload = create_payment_session_payload(order=attempt.order, reference=attempt.payment_reference)
            response = Response(PaymentSessionSerializer(payload).data, status=status.HTTP_200_OK)
            attach_idempotency_headers(response, replayed=True)
            return response

        reference = f"PAY-{order.order_number}-{timezone.now():%H%M%S}"
        try:
            attempt = PaymentAttempt.objects.create(
                order=order,
                provider=settings.PAYMENT_PROVIDER_NAME,
                payment_reference=reference,
                status="pending",
                amount=order.total,
                raw_payload={"source": "customer_checkout"},
            )
        except Exception:
            abort_idempotent_request(cache_key=idempotency_cache_key)
            raise
        record_order_event(
            order=order,
            event_type="payment_session_started",
            summary=f"Started payment session {attempt.payment_reference}.",
            actor=request.user,
            meta={"provider": attempt.provider, "payment_reference": attempt.payment_reference},
        )
        payload = create_payment_session_payload(order=order, reference=reference)
        complete_idempotent_request(
            cache_key=idempotency_cache_key,
            request=request,
            value={"payment_reference": attempt.payment_reference},
        )
        response = Response(PaymentSessionSerializer(payload).data)
        attach_idempotency_headers(response, replayed=False)
        return response


class OrderPaymentRetryView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "finance.make_payment"
    throttle_classes = [PaymentSessionThrottle]

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order.objects.filter(user=request.user), order_number=order_number)

        if order.payment_method == "COD":
            return Response({"detail": "Cash on Delivery orders do not require payment retry."}, status=status.HTTP_400_BAD_REQUEST)

        if order.payment_status not in {"failed", "pending"}:
            return Response({"detail": "Only failed or pending orders can start a retry."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idempotency_cache_key, replay = begin_idempotent_request(request=request, namespace="payment-retry")
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IdempotencyInProgress as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        if replay:
            attempt = generics.get_object_or_404(
                PaymentAttempt.objects.select_related("order").filter(order__user=request.user),
                payment_reference=replay.value["payment_reference"],
            )
            payload = create_payment_session_payload(order=attempt.order, reference=attempt.payment_reference)
            payload["checkout_url"] = f"/account/orders/{attempt.order.order_number}?retry={attempt.payment_reference}"
            response = Response(PaymentSessionSerializer(payload).data, status=status.HTTP_200_OK)
            attach_idempotency_headers(response, replayed=True)
            return response

        reference = f"PAY-{order.order_number}-retry-{timezone.now():%H%M%S}"
        try:
            attempt = PaymentAttempt.objects.create(
                order=order,
                provider=settings.PAYMENT_PROVIDER_NAME,
                payment_reference=reference,
                status="pending",
                amount=order.total,
                raw_payload={"source": "customer_retry"},
            )
        except Exception:
            abort_idempotent_request(cache_key=idempotency_cache_key)
            raise
        order.payment_status = "pending"
        order.save(update_fields=["payment_status", "updated_at"])
        sync_inventory_for_order(order=order, actor=request.user)
        sync_delivery_for_order_lifecycle(order=order, actor=request.user, notes="Payment retry started.")
        record_order_event(
            order=order,
            event_type="payment_retry_started",
            summary=f"Customer started a payment retry with reference {reference}.",
            actor=request.user,
            meta={"payment_reference": reference, "provider": attempt.provider},
        )
        create_order_notification(
            order=order,
            kind="payment_update",
            title="Payment retry started",
            body=f"You started another payment attempt for {order.order_number}.",
            meta={"payment_reference": reference},
        )
        payload = create_payment_session_payload(order=order, reference=reference)
        payload["checkout_url"] = f"/account/orders/{order.order_number}?retry={reference}"
        complete_idempotent_request(
            cache_key=idempotency_cache_key,
            request=request,
            value={"payment_reference": attempt.payment_reference},
        )
        response = Response(PaymentSessionSerializer(payload).data)
        attach_idempotency_headers(response, replayed=False)
        return response


class OrderRefundRequestView(APIView):
    permission_classes = [IsAuthenticated, HasMatrixPermission]
    required_matrix_permission = "finance.refund"

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order.objects.filter(user=request.user), order_number=order_number)
        serializer = RefundRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if order.payment_status != "paid":
            return Response({"detail": "Only paid orders can request a refund."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idempotency_cache_key, replay = begin_idempotent_request(request=request, namespace="refund-request")
        except IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except IdempotencyInProgress as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        if replay:
            order = (
                Order.objects.filter(user=request.user, order_number=order_number)
                .prefetch_related("items", "payment_attempts", "timeline", "refund_requests")
                .get()
            )
            response = Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)
            attach_idempotency_headers(response, replayed=True)
            return response

        latest_attempt = order.payment_attempts.order_by("-initiated_at").first()
        try:
            refund_request = RefundRequest.objects.create(
                order=order,
                payment_attempt=latest_attempt,
                requested_by=request.user,
                reason=serializer.validated_data["reason"],
                amount=order.total,
            )
        except Exception:
            abort_idempotent_request(cache_key=idempotency_cache_key)
            raise
        order.payment_status = "refund_pending"
        order.save(update_fields=["payment_status", "updated_at"])
        record_order_event(
            order=order,
            event_type="refund_requested",
            summary="Customer requested a refund.",
            actor=request.user,
            meta={"refund_request_id": refund_request.id},
        )
        create_order_notification(
            order=order,
            kind="payment_update",
            title="Refund requested",
            body=f"Your refund request for {order.order_number} is under review.",
            meta={"refund_request_id": refund_request.id},
        )
        order = Order.objects.filter(pk=order.pk).prefetch_related("items", "payment_attempts", "timeline", "refund_requests").get()
        complete_idempotent_request(
            cache_key=idempotency_cache_key,
            request=request,
            value={"refund_request_id": refund_request.id},
        )
        response = Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)
        attach_idempotency_headers(response, replayed=False)
        return response


class PaymentWebhookView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PaymentWebhookThrottle]

    def post(self, request):
        verify_payment_webhook(request)
        normalized_event = parse_payment_webhook(request)
        webhook_event, is_duplicate = register_webhook_event(request)
        if is_duplicate:
            return Response(
                {
                    "status": "duplicate_ignored",
                    "event": PaymentWebhookEventSerializer(webhook_event).data,
                },
                status=status.HTTP_200_OK,
            )
        payment_reference = normalized_event.payment_reference
        order_number = normalized_event.order_number
        event_status = normalized_event.normalized_status

        if not payment_reference and not order_number:
            return Response({"detail": "payment_reference or order_number is required."}, status=status.HTTP_400_BAD_REQUEST)

        attempt = None
        if payment_reference:
            attempt = PaymentAttempt.objects.filter(payment_reference=payment_reference).select_related("order").first()

        order = attempt.order if attempt else Order.objects.filter(order_number=order_number).first()
        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if not attempt:
            attempt = PaymentAttempt.objects.create(
                order=order,
                provider=normalized_event.provider,
                payment_reference=payment_reference or f"PAY-{order.order_number}-webhook",
                status="created",
                amount=order.total,
                raw_payload=normalized_event.raw_payload,
            )

        if event_status in {"authorized", "captured", "paid", "success"}:
            attempt.status = "captured" if event_status in {"captured", "paid", "success"} else "authorized"
            attempt.confirmed_at = timezone.now()
            order.payment_status = "paid"
            if order.status == "placed":
                order.status = "confirmed"
            order.save(update_fields=["payment_status", "status", "updated_at"])
            invoice = issue_invoice_for_order(order)
            sync_inventory_for_order(order=order, actor_label=normalized_event.provider)
            sync_delivery_for_order_lifecycle(order=order, notes="Webhook confirmed payment.")
            record_order_event(
                order=order,
                event_type="payment_captured",
                summary=f"Webhook marked payment {attempt.payment_reference} as {attempt.status}.",
                actor_label=normalized_event.provider,
                meta={
                    "provider": attempt.provider,
                    "payment_reference": attempt.payment_reference,
                    "invoice_number": invoice.invoice_number if invoice else "",
                },
            )
            create_order_notification(
                order=order,
                kind="payment_update",
                title="Payment update received",
                body=f"{order.order_number} payment is now {order.payment_status}.",
                meta={"payment_reference": attempt.payment_reference},
            )
            mark_webhook_processed(webhook_event, event_type=event_status)
        elif event_status in {"failed", "failure"}:
            attempt.status = "failed"
            order.payment_status = "failed"
            order.save(update_fields=["payment_status", "updated_at"])
            sync_inventory_for_order(order=order, actor_label=normalized_event.provider)
            sync_delivery_for_order_lifecycle(order=order, notes="Webhook marked payment failed.")
            record_order_event(
                order=order,
                event_type="payment_failed",
                summary=f"Webhook marked payment {attempt.payment_reference} as failed.",
                actor_label=normalized_event.provider,
                meta={"provider": attempt.provider, "payment_reference": attempt.payment_reference},
            )
            create_order_notification(
                order=order,
                kind="payment_update",
                title="Payment attempt failed",
                body=f"{order.order_number} payment could not be completed. You can retry from order detail.",
                meta={"payment_reference": attempt.payment_reference},
            )
            mark_webhook_processed(webhook_event, event_type=event_status)
        elif event_status in {"refund_pending", "refund_initiated", "refund_queued"}:
            order.payment_status = "refund_pending"
            order.save(update_fields=["payment_status", "updated_at"])
            RefundRequest.objects.filter(order=order, status="requested").update(
                status="approved",
                updated_at=timezone.now(),
            )
            record_order_event(
                order=order,
                event_type="refund_requested",
                summary=f"Webhook marked refund {attempt.payment_reference} as in progress.",
                actor_label=normalized_event.provider,
                meta={"provider": attempt.provider, "payment_reference": attempt.payment_reference},
            )
            create_order_notification(
                order=order,
                kind="payment_update",
                title="Refund in progress",
                body=f"Refund for {order.order_number} has been accepted and is processing.",
                meta={"payment_reference": attempt.payment_reference},
            )
            mark_webhook_processed(webhook_event, event_type=event_status)
        elif event_status in {"refunded", "refund_processed"}:
            attempt.status = "refunded"
            order.payment_status = "refunded"
            order.fulfillment_status = "returned"
            order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])
            sync_inventory_for_order(order=order, actor_label=normalized_event.provider)
            sync_delivery_for_order_lifecycle(order=order, notes="Webhook completed refund and return.")
            RefundRequest.objects.filter(order=order, status__in=["requested", "approved"]).update(
                status="processed",
                processed_at=timezone.now(),
                updated_at=timezone.now(),
            )
            record_order_event(
                order=order,
                event_type="refund_completed",
                summary=f"Webhook marked refund {attempt.payment_reference} as completed.",
                actor_label=normalized_event.provider,
                meta={"provider": attempt.provider, "payment_reference": attempt.payment_reference},
            )
            create_order_notification(
                order=order,
                kind="payment_update",
                title="Refund completed",
                body=f"Refund for {order.order_number} has been completed.",
                meta={"payment_reference": attempt.payment_reference},
            )
            mark_webhook_processed(webhook_event, event_type=event_status)
        else:
            attempt.status = "pending"
            mark_webhook_processed(webhook_event, event_type=event_status or "pending")

        attempt.raw_payload = normalized_event.raw_payload
        attempt.save(update_fields=["status", "confirmed_at", "raw_payload"])
        return Response(OrderSerializer(order).data)


class AdminSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = [
        "orders.view_orders",
        "finance.view_transactions",
        "inventory_warehouse.view_stock",
        "medicine_catalog.view_medicines",
        "prescription_management.view",
        "reports.view_reports",
    ]

    def get(self, request):
        from platform_apps.inventory.services import inventory_risk_snapshot
        from platform_apps.delivery.services import delivery_metrics_snapshot

        aggregate = Order.objects.aggregate(
            total_orders=Count("id"),
            total_revenue=Sum("total"),
        )
        pending_review = Prescription.objects.filter(status__in=["pending_review", "clarification_required"]).count()
        today_orders = Order.objects.filter(created_at__date=timezone.localdate()).count()
        recent_orders = Order.objects.order_by("-created_at")[:5]
        inventory_risk = inventory_risk_snapshot()
        delivery_metrics = delivery_metrics_snapshot()

        return Response(
            {
                "total_orders": aggregate["total_orders"] or 0,
                "today_orders": today_orders,
                "total_revenue": str(aggregate["total_revenue"] or Decimal("0.00")),
                "pending_prescription_review": pending_review,
                "catalog_products": Product.objects.filter(is_active=True).count(),
                "customers": User.objects.filter(role="customer").count(),
                "saved_addresses": CustomerAddress.objects.count(),
                "saved_payment_methods": SavedPaymentMethod.objects.filter(is_active=True).count(),
                "low_stock_products": inventory_risk["low_stock_count"],
                "out_of_stock_products": inventory_risk["out_of_stock_count"],
                "queued_fulfillment_orders": Order.objects.filter(fulfillment_status__in=["queued", "packed"]).count(),
                "shipped_orders": Order.objects.filter(fulfillment_status="shipped").count(),
                "dispatch_ready_shipments": delivery_metrics["dispatch_ready_shipments"],
                "delivery_in_transit": delivery_metrics["in_transit_shipments"],
                "delivery_failed": delivery_metrics["failed_shipments"],
                "delivery_returned": delivery_metrics["returned_shipments"],
                "delivery_reattempt_due": delivery_metrics["reattempt_due_shipments"],
                "delivery_sla_breached": delivery_metrics["sla_breached_shipments"],
                "recent_orders": OrderSerializer(recent_orders, many=True).data,
            }
        )


class AdminOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "orders.view_orders"
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.select_related("user", "delivery_shipment", "delivery_shipment__zone").prefetch_related("items", "payment_attempts").order_by("-created_at")
        status_value = self.request.query_params.get("status", "").strip()
        payment_status_value = self.request.query_params.get("payment_status", "").strip()
        fulfillment_status_value = self.request.query_params.get("fulfillment_status", "").strip()
        if status_value:
            queryset = queryset.filter(status=status_value)
        if payment_status_value:
            queryset = queryset.filter(payment_status=payment_status_value)
        if fulfillment_status_value:
            queryset = queryset.filter(fulfillment_status=fulfillment_status_value)
        return queryset


class AdminOrderDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "orders.view_orders",
        "PATCH": "orders.process_order",
        "PUT": "orders.process_order",
    }
    lookup_field = "order_number"

    def get_queryset(self):
        return Order.objects.select_related("delivery_shipment", "delivery_shipment__zone").prefetch_related("items", "payment_attempts", "timeline", "refund_requests", "delivery_shipment__events", "delivery_shipment__events__created_by")

    def get_serializer_class(self):
        if self.request.method in {"PATCH", "PUT"}:
            return AdminOrderUpdateSerializer
        return OrderDetailSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(OrderDetailSerializer(instance).data)

    def perform_update(self, serializer):
        instance = self.get_object()
        before_status = instance.status
        before_payment_status = instance.payment_status
        before_fulfillment_status = instance.fulfillment_status
        before_tracking_reference = instance.tracking_reference
        before_notes = instance.notes
        updated = serializer.save()
        changed = []
        if updated.status == "cancelled" and updated.fulfillment_status != "returned":
            updated.fulfillment_status = "cancelled"
            updated.save(update_fields=["fulfillment_status", "updated_at"])
        if updated.status != before_status:
            changed.append(f"status: {before_status} -> {updated.status}")
            record_order_event(
                order=updated,
                event_type="status_updated",
                summary=f"Admin updated status from {before_status} to {updated.status}.",
                actor=self.request.user,
                meta={"before": before_status, "after": updated.status},
            )
        if updated.payment_status != before_payment_status:
            changed.append(f"payment: {before_payment_status} -> {updated.payment_status}")
            record_order_event(
                order=updated,
                event_type="payment_status_updated",
                summary=f"Admin updated payment status from {before_payment_status} to {updated.payment_status}.",
                actor=self.request.user,
                meta={"before": before_payment_status, "after": updated.payment_status},
            )
            create_order_notification(
                order=updated,
                kind="payment_update",
                title="Payment status updated",
                body=f"{updated.order_number} payment is now {updated.payment_status.replace('_', ' ')}.",
                meta={"actor": self.request.user.role},
            )
        if updated.fulfillment_status != before_fulfillment_status:
            changed.append(f"fulfillment: {before_fulfillment_status} -> {updated.fulfillment_status}")
            record_order_event(
                order=updated,
                event_type="fulfillment_updated",
                summary=f"Admin updated fulfillment from {before_fulfillment_status} to {updated.fulfillment_status}.",
                actor=self.request.user,
                meta={"before": before_fulfillment_status, "after": updated.fulfillment_status},
            )
            create_order_notification(
                order=updated,
                kind="order_update",
                title="Fulfillment updated",
                body=f"{updated.order_number} fulfillment is now {updated.fulfillment_status.replace('_', ' ')}.",
                meta={"actor": self.request.user.role, "tracking_reference": updated.tracking_reference},
            )
        if updated.tracking_reference != before_tracking_reference:
            changed.append("tracking updated")
        if updated.status != before_status or updated.payment_status != before_payment_status:
            sync_inventory_for_order(order=updated, actor=self.request.user)
        if updated.fulfillment_status != before_fulfillment_status:
            sync_inventory_for_order(order=updated, actor=self.request.user)
        if (
            updated.status != before_status
            or updated.payment_status != before_payment_status
            or updated.fulfillment_status != before_fulfillment_status
            or updated.tracking_reference != before_tracking_reference
        ):
            sync_delivery_for_order_lifecycle(order=updated, actor=self.request.user, notes="Admin updated order delivery workflow.")
        if updated.notes != before_notes:
            changed.append("notes updated")
            record_order_event(
                order=updated,
                event_type="note_updated",
                summary="Admin updated internal order notes.",
                actor=self.request.user,
            )
        if changed:
            record_audit_event(
                actor=self.request.user,
                event_type="admin_order_updated",
                entity_type="order",
                entity_id=updated.order_number,
                severity="warning" if updated.status == "cancelled" else "info",
                message=f"{updated.order_number} updated by {self.request.user.role}.",
                meta={
                    "changes": changed,
                    "status": updated.status,
                    "payment_status": updated.payment_status,
                    "fulfillment_status": updated.fulfillment_status,
                },
            )
            create_order_notification(
                order=updated,
                kind="order_update",
                title="Order updated by support",
                body=f"{updated.order_number} changed: {', '.join(changed)}.",
                meta={"actor": self.request.user.role},
            )


class AdminPaymentAttemptListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "finance.view_transactions"
    serializer_class = AdminPaymentAttemptSerializer

    def get_queryset(self):
        queryset = PaymentAttempt.objects.select_related("order", "order__user").order_by("-initiated_at")
        status_value = self.request.query_params.get("status", "").strip()
        provider_value = self.request.query_params.get("provider", "").strip()
        if status_value:
            queryset = queryset.filter(status=status_value)
        if provider_value:
            queryset = queryset.filter(provider=provider_value)
        return queryset


def parse_date_range_params(request):
    from_value = request.query_params.get("from", "").strip()
    to_value = request.query_params.get("to", "").strip()
    try:
        period_start = timezone.datetime.fromisoformat(from_value) if from_value else None
    except ValueError as exc:
        raise ValidationError({"from": "Enter a valid ISO 8601 datetime."}) from exc
    try:
        period_end = timezone.datetime.fromisoformat(to_value) if to_value else None
    except ValueError as exc:
        raise ValidationError({"to": "Enter a valid ISO 8601 datetime."}) from exc
    if period_start and timezone.is_naive(period_start):
        period_start = timezone.make_aware(period_start, timezone.get_current_timezone())
    if period_end and timezone.is_naive(period_end):
        period_end = timezone.make_aware(period_end, timezone.get_current_timezone())
    return period_start, period_end


def filter_reconciliation_queryset(request):
    provider = request.query_params.get("provider", "").strip()
    period_start, period_end = parse_date_range_params(request)
    attempts = PaymentAttempt.objects.all()
    refunds = RefundRequest.objects.all()
    webhooks = PaymentWebhookEvent.objects.all()
    if provider:
        attempts = attempts.filter(provider=provider)
        webhooks = webhooks.filter(provider=provider)
    if period_start:
        attempts = attempts.filter(initiated_at__gte=period_start)
        refunds = refunds.filter(created_at__gte=period_start)
        webhooks = webhooks.filter(created_at__gte=period_start)
    if period_end:
        attempts = attempts.filter(initiated_at__lte=period_end)
        refunds = refunds.filter(created_at__lte=period_end)
        webhooks = webhooks.filter(created_at__lte=period_end)
    return attempts, refunds, webhooks


def filtered_snapshot_queryset(request):
    queryset = ReconciliationSnapshot.objects.all()
    provider = request.query_params.get("provider", "").strip()
    period_start, period_end = parse_date_range_params(request)
    if provider:
        queryset = queryset.filter(provider=provider)
    if period_start:
        queryset = queryset.filter(created_at__gte=period_start)
    if period_end:
        queryset = queryset.filter(created_at__lte=period_end)
    return queryset


def filtered_settlement_queryset(request):
    queryset = SettlementBatch.objects.prefetch_related("entries__order", "entries__payment_attempt", "entries__refund_request")
    provider = request.query_params.get("provider", "").strip()
    period_start, period_end = parse_date_range_params(request)
    if provider:
        queryset = queryset.filter(provider=provider)
    if period_start:
        queryset = queryset.filter(period_end__gte=period_start)
    if period_end:
        queryset = queryset.filter(period_start__lte=period_end)
    return queryset.order_by("-created_at")


class AdminReconciliationSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "finance.view_transactions",
        "POST": "finance.view_transactions",
    }

    def get(self, request):
        attempts, refunds, webhooks = filter_reconciliation_queryset(request)
        captured_total = attempts.filter(status="captured").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        refunded_total = refunds.filter(status="processed").aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        pending_refunds = refunds.filter(status__in=["requested", "approved"]).count()
        unmatched_paid_orders = (
            Order.objects.filter(id__in=attempts.values_list("order_id", flat=True), payment_status="paid")
            .exclude(payment_attempts__status__in=["captured", "refunded"])
            .count()
        )

        return Response(
            {
                "provider": settings.PAYMENT_PROVIDER_NAME,
                "attempt_count": attempts.count(),
                "captured_total": str(captured_total),
                "refunded_total": str(refunded_total),
                "pending_refund_count": pending_refunds,
                "duplicate_webhooks": webhooks.filter(was_duplicate=True).count(),
                "processed_webhooks": webhooks.filter(processed_at__isnull=False).count(),
                "unmatched_paid_orders": unmatched_paid_orders,
                "latest_webhooks": PaymentWebhookEventSerializer(webhooks[:10], many=True).data,
                "snapshot_history": ReconciliationSnapshotSerializer(filtered_snapshot_queryset(request)[:12], many=True).data,
                "settlement_history": SettlementBatchSerializer(filtered_settlement_queryset(request)[:12], many=True).data,
            }
        )

    def post(self, request):
        notes = str(request.data.get("notes", "")).strip()
        snapshot = build_reconciliation_snapshot(
            created_by_label=request.user.full_name or request.user.phone_number,
            notes=notes,
        )
        record_audit_event(
            actor=request.user,
            event_type="reconciliation_snapshot_created",
            entity_type="reconciliation_snapshot",
            entity_id=snapshot.id,
            message=f"Captured reconciliation snapshot for {snapshot.provider}.",
            meta={"provider": snapshot.provider, "notes_present": bool(notes)},
        )
        return Response(ReconciliationSnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)


class AdminReconciliationExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "reports.export_reports"

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="payment-reconciliation.csv"'
        response.write("order_number,payment_reference,provider,status,amount,payment_status,refund_status,initiated_at,confirmed_at\r\n")

        attempts, _, _ = filter_reconciliation_queryset(request)
        for attempt in attempts.select_related("order").order_by("-initiated_at"):
            latest_refund = attempt.refund_requests.order_by("-created_at").first()
            response.write(
                f"{attempt.order.order_number},{attempt.payment_reference},{attempt.provider},{attempt.status},"
                f"{attempt.amount},{attempt.order.payment_status},{latest_refund.status if latest_refund else ''},"
                f"{attempt.initiated_at.isoformat()},{attempt.confirmed_at.isoformat() if attempt.confirmed_at else ''}\r\n"
            )

        return response


class AdminSettlementBatchListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "finance.view_transactions",
        "POST": "finance.payouts",
    }

    def get(self, request):
        return Response(SettlementBatchSerializer(filtered_settlement_queryset(request), many=True).data)

    def post(self, request):
        serializer = SettlementBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        period_start = serializer.validated_data.get("period_start") or timezone.now() - timezone.timedelta(days=30)
        period_end = serializer.validated_data.get("period_end") or timezone.now()
        provider = serializer.validated_data.get("provider") or settings.PAYMENT_PROVIDER_NAME
        notes = serializer.validated_data.get("notes", "")
        attempts = (
            PaymentAttempt.objects.select_related("order")
            .filter(provider=provider, initiated_at__gte=period_start, initiated_at__lte=period_end, status__in=["captured", "refunded"])
            .exclude(settlement_entries__isnull=False)
            .order_by("initiated_at")
        )
        batch = SettlementBatch.objects.create(
            provider=provider,
            batch_reference=f"SET-{timezone.localtime():%Y%m%d%H%M%S}",
            period_start=period_start,
            period_end=period_end,
            status="draft",
            created_by=request.user,
            notes=notes,
        )
        total_captured = Decimal("0.00")
        total_refunded = Decimal("0.00")
        total_net = Decimal("0.00")
        for attempt in attempts:
            refund_request = attempt.order.refund_requests.filter(status="processed").order_by("-created_at").first()
            gross_amount = Decimal(attempt.amount)
            refund_amount = Decimal(refund_request.amount) if refund_request else Decimal("0.00")
            net_amount = gross_amount - refund_amount
            settlement_status = "refunded" if refund_amount > 0 else "settled"
            SettlementEntry.objects.create(
                settlement_batch=batch,
                order=attempt.order,
                payment_attempt=attempt,
                refund_request=refund_request,
                gross_amount=gross_amount,
                refund_amount=refund_amount,
                net_amount=net_amount,
                settlement_status=settlement_status if refund_amount == 0 or net_amount == 0 else "netted",
            )
            total_captured += gross_amount
            total_refunded += refund_amount
            total_net += net_amount
        batch.total_captured = total_captured
        batch.total_refunded = total_refunded
        batch.total_net = total_net
        batch.save(update_fields=["total_captured", "total_refunded", "total_net"])
        record_audit_event(
            actor=request.user,
            event_type="settlement_batch_created",
            entity_type="settlement_batch",
            entity_id=batch.id,
            message=f"Created settlement batch {batch.batch_reference}.",
            meta={"provider": batch.provider, "entry_count": batch.entries.count(), "status": batch.status},
        )
        return Response(SettlementBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


class AdminSettlementBatchDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "finance.view_transactions"
    serializer_class = SettlementBatchSerializer
    queryset = SettlementBatch.objects.prefetch_related("entries__order", "entries__payment_attempt", "entries__refund_request")
    lookup_field = "id"


class AdminSettlementBatchUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "finance.payouts"

    def post(self, request, id):
        batch = generics.get_object_or_404(SettlementBatch, pk=id)
        serializer = SettlementBatchUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        update_fields = []
        next_status = serializer.validated_data.get("status")
        next_notes = serializer.validated_data.get("notes")

        if next_status and next_status != batch.status:
            batch.status = next_status
            update_fields.append("status")

        if next_notes is not None and next_notes != batch.notes:
            batch.notes = next_notes
            update_fields.append("notes")

        if update_fields:
            batch.save(update_fields=update_fields)
            record_audit_event(
                actor=request.user,
                event_type="settlement_batch_updated",
                entity_type="settlement_batch",
                entity_id=batch.id,
                message=f"Updated settlement batch {batch.batch_reference}.",
                meta={"updated_fields": update_fields, "status": batch.status},
            )

        refreshed = SettlementBatch.objects.prefetch_related(
            "entries__order",
            "entries__payment_attempt",
            "entries__refund_request",
        ).get(pk=batch.pk)
        return Response(SettlementBatchSerializer(refreshed).data)


class AdminSettlementBatchExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "reports.export_reports"

    def get(self, request, batch_id):
        batch = generics.get_object_or_404(
            SettlementBatch.objects.prefetch_related("entries__order", "entries__payment_attempt", "entries__refund_request"),
            pk=batch_id,
        )
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="settlement-{batch.batch_reference}.csv"'
        response.write("batch_reference,order_number,payment_reference,gross_amount,refund_amount,net_amount,settlement_status\r\n")
        for entry in batch.entries.all():
            response.write(
                f"{batch.batch_reference},{entry.order.order_number},{entry.payment_attempt.payment_reference},"
                f"{entry.gross_amount},{entry.refund_amount},{entry.net_amount},{entry.settlement_status}\r\n"
            )
        return response


class AdminRefundDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrOps, HasMatrixPermission]
    required_matrix_permission = "finance.refund"

    def post(self, request, order_number):
        order = generics.get_object_or_404(Order, order_number=order_number)
        refund_request = order.refund_requests.order_by("-created_at").first()
        if not refund_request:
            return Response({"detail": "No refund request found for this order."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RefundRequestDecisionSerializer(refund_request, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        refund_request = serializer.save()
        record_audit_event(
            actor=request.user,
            event_type="refund_decision_recorded",
            entity_type="refund_request",
            entity_id=refund_request.id,
            severity="warning" if refund_request.status == "rejected" else "info",
            message=f"Refund for {order.order_number} set to {refund_request.status}.",
            meta={"order_number": order.order_number, "refund_status": refund_request.status},
        )

        if refund_request.status in {"approved", "processed"}:
            order.payment_status = "refunded" if refund_request.status == "processed" else "refund_pending"
            if refund_request.status == "processed":
                order.fulfillment_status = "returned"
            order.save(update_fields=["payment_status", "fulfillment_status", "updated_at"])
            sync_inventory_for_order(order=order, actor=request.user)
            sync_delivery_for_order_lifecycle(order=order, actor=request.user, notes="Admin updated refund and return workflow.")
            latest_attempt = order.payment_attempts.order_by("-initiated_at").first()
            if latest_attempt and refund_request.status == "processed":
                latest_attempt.status = "refunded"
                latest_attempt.confirmed_at = timezone.now()
                latest_attempt.save(update_fields=["status", "confirmed_at"])
            record_order_event(
                order=order,
                event_type="refund_completed" if refund_request.status == "processed" else "refund_requested",
                summary=f"Admin set refund status to {refund_request.status}.",
                actor=request.user,
                meta={"refund_request_id": refund_request.id},
            )
            create_order_notification(
                order=order,
                kind="payment_update",
                title="Refund request updated",
                body=f"{order.order_number} refund status is now {refund_request.status}.",
                meta={"refund_request_id": refund_request.id},
            )
        elif refund_request.status == "rejected":
            order.payment_status = "paid"
            order.save(update_fields=["payment_status", "updated_at"])
            sync_inventory_for_order(order=order, actor=request.user)
            sync_delivery_for_order_lifecycle(order=order, actor=request.user, notes="Refund rejected, shipment remains active.")
            create_order_notification(
                order=order,
                kind="payment_update",
                title="Refund request rejected",
                body=f"{order.order_number} refund request was rejected.",
                meta={"refund_request_id": refund_request.id},
            )

        order = Order.objects.filter(pk=order.pk).prefetch_related("items", "payment_attempts", "timeline", "refund_requests").get()
        return Response(OrderDetailSerializer(order).data)
