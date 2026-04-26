from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Brand, Category, Product
from platform_apps.users.models import User


class CatalogAdminPermissionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.customer = User.objects.create_user(
            phone_number="9110000001",
            password="testpass123",
            role="customer",
            is_phone_verified=True,
        )
        self.catalog_manager = User.objects.create_user(
            phone_number="9110000002",
            password="testpass123",
            role="catalog_manager",
            is_staff=True,
            is_phone_verified=True,
        )

    def test_customer_cannot_open_admin_products(self) -> None:
        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/v1/catalog/admin/products/")

        self.assertEqual(response.status_code, 403)

    def test_catalog_manager_can_open_admin_products(self) -> None:
        self.client.force_authenticate(self.catalog_manager)

        response = self.client.get("/api/v1/catalog/admin/products/")

        self.assertEqual(response.status_code, 200)


class CatalogPublicResilienceTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()
        self.category = Category.objects.create(name="Pain Relief", slug="pain-relief")
        self.brand = Brand.objects.create(name="TrueCare", slug="truecare")
        self.product = Product.objects.create(
            name="Paracetamol 650",
            slug="paracetamol-650",
            sku="PARA650",
            category=self.category,
            brand=self.brand,
            manufacturer="TrueCare Labs",
            composition="Paracetamol",
            mrp="50.00",
            sale_price="42.00",
            stock_status="in_stock",
        )

    def test_product_list_sets_cache_headers_and_hits_cache(self) -> None:
        first = self.client.get("/api/v1/catalog/products/")
        second = self.client.get("/api/v1/catalog/products/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["X-Cache"], "MISS")
        self.assertIn("max-age=120", first.headers["Cache-Control"])
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.headers["X-Cache"], "HIT")
        self.assertEqual(first.data[0]["slug"], self.product.slug)
        self.assertEqual(second.data[0]["slug"], self.product.slug)

    def test_search_requests_are_throttled_more_aggressively(self) -> None:
        with patch.dict(
            "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
            {"public_catalog_read": "10/minute", "public_catalog_search": "1/minute"},
            clear=False,
        ):
            first = self.client.get("/api/v1/catalog/products/?q=para")
            second = self.client.get("/api/v1/catalog/products/?q=para")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
