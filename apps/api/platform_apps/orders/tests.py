import hashlib
import hmac
from uuid import uuid4
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from platform_apps.cart.models import Cart, CartItem
from platform_apps.catalog.models import Brand, Category, Product
from .adapters import RazorpayAdapter
from .models import Invoice, Order, PaymentAttempt
from platform_apps.users.models import RolePermissionMatrix, User
from platform_apps.users.views import ensure_role_permission_matrices


class OrderAdminPermissionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9440000001",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.finance_user = User.objects.create_user(
            phone_number="9440000002",
            password="testpass123",
            role="finance",
            is_staff=True,
            is_phone_verified=True,
        )

    def test_customer_cannot_open_admin_summary(self) -> None:
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/orders/admin-summary/")

        self.assertEqual(response.status_code, 403)

    def test_finance_user_can_open_admin_summary(self) -> None:
        self.client.force_authenticate(self.finance_user)

        response = self.client.get("/api/v1/orders/admin-summary/")

        self.assertEqual(response.status_code, 200)

    def test_finance_user_denied_admin_payments_when_matrix_blocks_transactions(self) -> None:
        ensure_role_permission_matrices()
        matrix = RolePermissionMatrix.objects.get(role="finance")
        matrix.matrix_permissions["finance.view_transactions"] = "denied"
        matrix.save(update_fields=["matrix_permissions", "updated_at"])

        self.client.force_authenticate(self.finance_user)

        response = self.client.get("/api/v1/orders/admin-payments/")

        self.assertEqual(response.status_code, 403)


class OrderIdempotencyTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9440000011",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.category = Category.objects.create(name="Pain Relief", slug="pain-relief")
        self.brand = Brand.objects.create(name="TrueCare", slug="truecare")
        self.product = Product.objects.create(
            name="Paracetamol 650",
            slug="paracetamol-650",
            sku="PARA650-TEST",
            category=self.category,
            brand=self.brand,
            manufacturer="TrueCare Labs",
            composition="Paracetamol",
            mrp="50.00",
            sale_price="42.00",
        )
        self.client.force_authenticate(self.customer)

    def test_order_list_respects_matrix_view_orders_permission(self) -> None:
        ensure_role_permission_matrices()
        matrix = RolePermissionMatrix.objects.get(role="customer")
        matrix.matrix_permissions["orders.view_orders"] = "denied"
        matrix.save(update_fields=["matrix_permissions", "updated_at"])

        response = self.client.get("/api/v1/orders/")

        self.assertEqual(response.status_code, 403)

    def test_checkout_replays_with_same_idempotency_key(self) -> None:
        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            product_slug=self.product.slug,
            name=self.product.name,
            mrp="50.00",
            sale_price="42.00",
            qty=1,
        )

        payload = {
            "address": {
                "label": "Home",
                "recipient": "Rakesh",
                "line1": "Street 1",
                "city": "Mumbai",
                "pincode": "400001",
            },
            "payment_method": "COD",
            "notes": "Leave at door",
        }

        with (
            patch("platform_apps.orders.serializers.reserve_stock_for_order"),
            patch("platform_apps.orders.serializers.sync_delivery_for_order"),
        ):
            idempotency_key = f"checkout-{uuid4()}"
            first = self.client.post("/api/v1/orders/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY=idempotency_key)
            second = self.client.post("/api/v1/orders/checkout/", payload, format="json", HTTP_IDEMPOTENCY_KEY=idempotency_key)

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data["order_number"], second.data["order_number"])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(first.headers["X-Idempotent-Replay"], "false")
        self.assertEqual(second.headers["X-Idempotent-Replay"], "true")

    def test_payment_session_replays_same_attempt(self) -> None:
        order = Order.objects.create(
            user=self.customer,
            order_number="TC-SESSION-1",
            status="placed",
            payment_method="UPI",
            payment_status="pending",
            recipient="Rakesh",
            line1="Street 1",
            city="Mumbai",
            pincode="400001",
            subtotal="42.00",
            discount="8.00",
            delivery_fee="40.00",
            total="82.00",
        )

        def build_payload(*, order, reference):
            return {
                "order_number": order.order_number,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "amount": order.total,
                "provider": "simulated_gateway",
                "provider_key": "test-key",
                "payment_reference": reference,
                "checkout_url": f"/pay/{reference}",
            }

        with patch("platform_apps.orders.views.create_payment_session_payload", side_effect=build_payload):
            idempotency_key = f"session-{uuid4()}"
            first = self.client.post(
                f"/api/v1/orders/{order.order_number}/payment/session/",
                {},
                format="json",
                HTTP_IDEMPOTENCY_KEY=idempotency_key,
            )
            second = self.client.post(
                f"/api/v1/orders/{order.order_number}/payment/session/",
                {},
                format="json",
                HTTP_IDEMPOTENCY_KEY=idempotency_key,
            )

        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(PaymentAttempt.objects.count(), 1)
        self.assertEqual(first.data["payment_reference"], second.data["payment_reference"])
        self.assertEqual(second.headers["X-Idempotent-Replay"], "true")


class OrderInvoiceTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9440000091",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.client.force_authenticate(self.customer)
        self.order = Order.objects.create(
            user=self.customer,
            order_number="TC-INVOICE-1",
            status="placed",
            payment_method="UPI",
            payment_status="pending",
            recipient="Rakesh",
            line1="Street 1",
            city="Mumbai",
            pincode="400001",
            subtotal="84.00",
            discount="4.00",
            delivery_fee="40.00",
            total="120.00",
        )
        PaymentAttempt.objects.create(
            order=self.order,
            provider="simulated_gateway",
            payment_reference="PAY-TC-INVOICE-1",
            status="pending",
            amount="120.00",
        )

    def test_confirm_payment_issues_invoice(self) -> None:
        response = self.client.post(f"/api/v1/orders/{self.order.order_number}/payment/confirm/")

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        invoice = Invoice.objects.get(order=self.order)
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(invoice.total, self.order.total)
        self.assertEqual(response.data["invoice"]["invoice_number"], invoice.invoice_number)
        self.assertEqual(response.data["invoice"]["snapshot"]["order_number"], self.order.order_number)

    def test_customer_can_download_invoice_after_payment(self) -> None:
        self.client.post(f"/api/v1/orders/{self.order.order_number}/payment/confirm/")

        response = self.client.get(f"/api/v1/orders/{self.order.order_number}/invoice/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        self.assertIn("INV-", response.content.decode("utf-8"))

    def test_invoice_download_is_missing_before_payment(self) -> None:
        response = self.client.get(f"/api/v1/orders/{self.order.order_number}/invoice/")

        self.assertEqual(response.status_code, 404)


@override_settings(
    PAYMENT_PROVIDER_NAME="razorpay",
    PAYMENT_PROVIDER_PUBLIC_KEY="rzp_test_key",
    PAYMENT_PROVIDER_SECRET_KEY="rzp_test_secret",
)
class RazorpayAdapterTests(TestCase):
    def test_create_payment_session_creates_and_persists_razorpay_order(self) -> None:
        customer = User.objects.create_user(
            phone_number="9440000092",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        order = Order.objects.create(
            user=customer,
            order_number="TC-RAZOR-1",
            status="placed",
            payment_method="UPI",
            payment_status="pending",
            recipient="Rakesh",
            line1="Street 1",
            city="Mumbai",
            pincode="400001",
            subtotal="84.00",
            discount="4.00",
            delivery_fee="40.00",
            total="120.00",
        )
        attempt = PaymentAttempt.objects.create(
            order=order,
            provider="razorpay",
            payment_reference="PAY-TC-RAZOR-1",
            status="pending",
            amount="120.00",
            raw_payload={"source": "customer_checkout"},
        )

        with patch.object(
            RazorpayAdapter,
            "_request_json",
            return_value={"id": "order_test123", "amount": 12000, "currency": "INR"},
        ) as request_mock:
            payload = RazorpayAdapter().create_payment_session(order=order, attempt=attempt)

        attempt.refresh_from_db()
        self.assertEqual(request_mock.call_count, 1)
        self.assertEqual(payload["provider_order_id"], "order_test123")
        self.assertEqual(payload["provider_currency"], "INR")
        self.assertEqual(attempt.raw_payload["provider_order_id"], "order_test123")
        self.assertEqual(attempt.raw_payload["provider_amount"], 12000)


@override_settings(
    PAYMENT_PROVIDER_NAME="razorpay",
    PAYMENT_PROVIDER_PUBLIC_KEY="rzp_test_key",
    PAYMENT_PROVIDER_SECRET_KEY="rzp_test_secret",
)
class RazorpayVerificationViewTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9440000093",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.client.force_authenticate(self.customer)
        self.order = Order.objects.create(
            user=self.customer,
            order_number="TC-RAZOR-VERIFY-1",
            status="placed",
            payment_method="UPI",
            payment_status="pending",
            recipient="Rakesh",
            line1="Street 1",
            city="Mumbai",
            pincode="400001",
            subtotal="84.00",
            discount="4.00",
            delivery_fee="40.00",
            total="120.00",
        )
        self.attempt = PaymentAttempt.objects.create(
            order=self.order,
            provider="razorpay",
            payment_reference="PAY-TC-RAZOR-VERIFY-1",
            status="pending",
            amount="120.00",
            raw_payload={"provider_order_id": "order_test123"},
        )

    def test_verify_view_marks_order_paid_when_signature_matches(self) -> None:
        payment_id = "pay_test456"
        order_id = "order_test123"
        signature = hmac.new(
            settings.PAYMENT_PROVIDER_SECRET_KEY.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            f"/api/v1/orders/{self.order.order_number}/payment/verify/",
            {
                "payment_reference": self.attempt.payment_reference,
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.attempt.refresh_from_db()
        self.assertEqual(self.order.payment_status, "paid")
        self.assertEqual(self.order.status, "confirmed")
        self.assertEqual(self.attempt.status, "captured")
        self.assertEqual(self.attempt.raw_payload["provider_payment_id"], payment_id)
