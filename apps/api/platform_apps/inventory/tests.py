from django.test import TestCase
from rest_framework.test import APIClient

from platform_apps.users.models import User


class InventoryAdminPermissionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9330000001",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.viewer = User.objects.create_user(
            phone_number="9330000002",
            password="testpass123",
            role="viewer",
            is_staff=True,
            is_phone_verified=True,
        )

    def test_customer_cannot_open_admin_inventory(self) -> None:
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/inventory/admin/items/")

        self.assertEqual(response.status_code, 403)

    def test_viewer_can_open_admin_inventory(self) -> None:
        self.client.force_authenticate(self.viewer)

        response = self.client.get("/api/v1/inventory/admin/items/")

        self.assertEqual(response.status_code, 200)
