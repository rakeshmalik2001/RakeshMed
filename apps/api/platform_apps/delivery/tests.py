from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from platform_apps.delivery.models import DeliveryShipment
from platform_apps.orders.models import Order
from platform_apps.users.models import User


class DeliveryAdminPermissionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9220000001",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.viewer = User.objects.create_user(
            phone_number="9220000002",
            password="testpass123",
            role="viewer",
            is_staff=True,
            is_phone_verified=True,
        )

    def test_customer_cannot_open_admin_shipments(self) -> None:
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/delivery/admin/shipments/")

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_open_admin_shipments(self) -> None:
        self.client.force_authenticate(self.viewer)

        response = self.client.get("/api/v1/delivery/admin/shipments/")

        self.assertEqual(response.status_code, 200)

    def test_admin_cannot_mark_blocked_shipment_delivered(self) -> None:
        admin_user = User.objects.create_user(
            phone_number="9220000003",
            password="testpass123",
            role="admin",
            is_staff=True,
            is_phone_verified=True,
        )
        order = Order.objects.create(
            user=self.customer,
            order_number="TC-DELIVERY-BLOCKED-1",
            status="placed",
            payment_method="UPI",
            payment_status="pending",
            inventory_status="unreserved",
            fulfillment_status="queued",
            recipient="Rakesh",
            line1="Street 1",
            city="Mumbai",
            pincode="400001",
            subtotal="84.00",
            discount="4.00",
            delivery_fee="40.00",
            total="120.00",
        )
        shipment = DeliveryShipment.objects.create(order=order, status="queued")
        self.client.force_authenticate(admin_user)

        response = self.client.patch(
            f"/api/v1/delivery/admin/shipments/{order.order_number}/",
            {"status": "delivered"},
            format="json",
        )

        shipment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertIn("Shipment is blocked:", str(response.data["status"]))
        self.assertEqual(shipment.status, "queued")
        self.assertEqual(order.fulfillment_status, "queued")


class DeliveryPublicResilienceTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()

    def test_serviceability_is_cached(self) -> None:
        first = self.client.get("/api/v1/delivery/serviceability/?pincode=400001")
        second = self.client.get("/api/v1/delivery/serviceability/?pincode=400001")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["X-Cache"], "MISS")
        self.assertEqual(second.headers["X-Cache"], "HIT")
        self.assertIn("max-age=300", second.headers["Cache-Control"])

    def test_serviceability_is_rate_limited(self) -> None:
        with patch.dict(
            "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
            {"public_serviceability": "1/minute"},
            clear=False,
        ):
            first = self.client.get("/api/v1/delivery/serviceability/?pincode=400001")
            second = self.client.get("/api/v1/delivery/serviceability/?pincode=400002")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
