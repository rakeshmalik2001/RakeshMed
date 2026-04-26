from django.test import TestCase
from rest_framework.test import APIClient

from platform_apps.audit.models import AuditLog
from platform_apps.catalog.models import Category, Product
from platform_apps.inventory.models import InventoryItem, StockLocation
from platform_apps.orders.models import Order
from platform_apps.prescriptions.models import Prescription
from platform_apps.users.models import User


class AuditWorkflowTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = User.objects.create_user(
            phone_number="9550000001",
            password="testpass123",
            full_name="Admin User",
            role="admin",
            is_staff=True,
            is_phone_verified=True,
        )
        self.pharmacist = User.objects.create_user(
            phone_number="9550000002",
            password="testpass123",
            full_name="Pharmacist User",
            role="pharmacist",
            is_staff=True,
            is_phone_verified=True,
        )
        self.customer = User.objects.create_user(
            phone_number="9550000003",
            password="testpass123",
            full_name="Customer User",
            role="customer",
            is_phone_verified=True,
        )
        self.category = Category.objects.create(name="Pain Relief", slug="pain-relief")
        self.product = Product.objects.create(
            name="Paracetamol 500",
            slug="paracetamol-500",
            sku="PCM500",
            category=self.category,
            manufacturer="RakeshMed Labs",
            mrp="30.00",
            sale_price="25.00",
            stock_status="in_stock",
        )
        self.location = StockLocation.objects.create(name="Main Warehouse", code="WH1")
        InventoryItem.objects.create(product=self.product, location=self.location, quantity_on_hand=10, reserved_quantity=0)
        self.order = Order.objects.create(
            user=self.customer,
            order_number="ORD-AUDIT-001",
            status="placed",
            payment_method="UPI",
            payment_status="pending",
            inventory_status="reserved",
            fulfillment_status="queued",
            recipient="Customer User",
            line1="123 Street",
            city="Bangalore",
            pincode="560001",
            subtotal="25.00",
            discount="0.00",
            delivery_fee="0.00",
            total="25.00",
        )
        self.prescription = Prescription.objects.create(
            user=self.customer,
            reference_code="RX-AUDIT-001",
            patient_name="Customer User",
            doctor_name="Dr. Sharma",
            uploaded_file_name="rx.png",
            uploaded_file_type="image/png",
            storage_key="prescriptions/rx.png",
            uploaded_file_size_bytes=128,
            status="pending_review",
        )

    def test_prescription_review_writes_audit_log(self) -> None:
        self.client.force_authenticate(self.pharmacist)

        response = self.client.post(
            f"/api/v1/prescriptions/pharmacist/queue/{self.prescription.reference_code}/review/",
            {"decision": "approved", "notes": "Legible and valid."},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        audit_log = AuditLog.objects.filter(event_type="prescription_reviewed").latest("created_at")
        self.assertEqual(audit_log.actor, self.pharmacist)
        self.assertEqual(audit_log.entity_id, self.prescription.reference_code)
        self.assertEqual(audit_log.meta["decision"], "approved")

    def test_admin_order_patch_writes_audit_log(self) -> None:
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            f"/api/v1/orders/admin-orders/{self.order.order_number}/",
            {"payment_status": "paid"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        audit_log = AuditLog.objects.filter(event_type="admin_order_updated").latest("created_at")
        self.assertEqual(audit_log.actor, self.admin)
        self.assertEqual(audit_log.entity_id, self.order.order_number)
        self.assertIn("payment: pending -> paid", audit_log.meta["changes"])

    def test_inventory_adjustment_writes_audit_log(self) -> None:
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            f"/api/v1/inventory/admin/items/{self.product.id}/",
            {"location_id": self.location.id, "quantity_delta": -8, "movement_type": "adjustment"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        audit_log = AuditLog.objects.filter(event_type="inventory_adjusted").latest("created_at")
        self.assertEqual(audit_log.actor, self.admin)
        self.assertEqual(str(audit_log.entity_id), str(self.product.id))
        self.assertEqual(audit_log.meta["movement_type"], "adjustment")
