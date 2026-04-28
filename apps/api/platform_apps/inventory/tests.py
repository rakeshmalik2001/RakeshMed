from django.test import TestCase
from rest_framework.test import APIClient

from platform_apps.catalog.models import Brand, Category, Product
from platform_apps.inventory.models import InventoryItem
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

    def test_warehouse_operator_cannot_make_inventory_negative(self) -> None:
        warehouse_user = User.objects.create_user(
            phone_number="9330000003",
            password="testpass123",
            role="warehouse_operator",
            is_staff=True,
            is_phone_verified=True,
        )
        category = Category.objects.create(name="Inventory Test", slug="inventory-test")
        brand = Brand.objects.create(name="Warehouse Brand", slug="warehouse-brand")
        product = Product.objects.create(
            name="Inventory Medicine",
            slug="inventory-medicine",
            sku="INV-MED-001",
            category=category,
            brand=brand,
            manufacturer="Warehouse Labs",
            mrp="50.00",
            sale_price="45.00",
        )
        self.client.force_authenticate(warehouse_user)
        existing_item = InventoryItem.objects.filter(product=product).first()
        previous_quantity = existing_item.quantity_on_hand if existing_item else 0

        response = self.client.patch(
            f"/api/v1/inventory/admin/items/{product.pk}/",
            {"quantity_on_hand": -1},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Quantity on hand cannot be negative.", str(response.data["quantity_on_hand"]))
        refreshed_item = InventoryItem.objects.filter(product=product).first()
        self.assertIsNotNone(refreshed_item)
        self.assertEqual(refreshed_item.quantity_on_hand, previous_quantity)
