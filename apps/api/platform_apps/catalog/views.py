from django.conf import settings
from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated

from config.api_resilience import CachedListAPIView, CachedRetrieveAPIView
from config.throttles import PublicCatalogReadThrottle, PublicCatalogSearchThrottle
from platform_apps.users.views import HasMatrixPermission

from .models import Brand, Category, Product
from .serializers import (
    AdminInventoryProductSerializer,
    AdminProductSerializer,
    BrandSerializer,
    CategorySerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class IsCatalogOps(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.role in {"admin", "catalog_manager", "warehouse_operator", "support_agent"}
            )
        )


class CategoryListView(CachedListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    throttle_classes = [PublicCatalogReadThrottle]
    cache_prefix = "catalog:categories"

    def get_queryset(self):
        return Category.objects.filter(is_active=True).select_related("parent").order_by("sort_order", "name")


class BrandListView(CachedListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BrandSerializer
    throttle_classes = [PublicCatalogReadThrottle]
    cache_prefix = "catalog:brands"

    def get_queryset(self):
        return Brand.objects.filter(is_active=True).order_by("name")


class ProductListView(CachedListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    throttle_classes = [PublicCatalogReadThrottle]
    cache_prefix = "catalog:products"

    def get_cache_timeout(self) -> int:
        if self.request.query_params.get("q", "").strip():
            return settings.PUBLIC_SEARCH_CACHE_TTL_SECONDS
        return settings.PUBLIC_API_CACHE_TTL_SECONDS

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.request.query_params.get("q", "").strip():
            throttles.append(PublicCatalogSearchThrottle())
        return throttles

    def get_queryset(self):
        queryset = (
            Product.objects.filter(is_active=True)
            .select_related("category", "brand")
            .order_by("name")
        )

        query = self.request.query_params.get("q", "").strip()
        category_slug = self.request.query_params.get("category", "").strip()
        brand_slug = self.request.query_params.get("brand", "").strip()
        prescription_required = self.request.query_params.get("prescription_required", "").strip().lower()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(composition__icontains=query)
                | Q(manufacturer__icontains=query)
                | Q(sku__icontains=query)
            )
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)
        if prescription_required in {"true", "false"}:
            queryset = queryset.filter(requires_prescription=(prescription_required == "true"))

        return queryset


class ProductDetailView(CachedRetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
    throttle_classes = [PublicCatalogReadThrottle]
    cache_prefix = "catalog:product-detail"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category", "brand").prefetch_related(
            "substitute_links__substitute_product__category",
            "substitute_links__substitute_product__brand",
        )


class AdminProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsCatalogOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "medicine_catalog.view_medicines",
        "POST": "medicine_catalog.add_medicine",
    }
    serializer_class = AdminProductSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related("category", "brand").order_by("name")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
                | Q(composition__icontains=query)
                | Q(manufacturer__icontains=query)
            )
        return queryset


class AdminProductDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsCatalogOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "medicine_catalog.view_medicines",
        "PATCH": "medicine_catalog.edit_medicine",
        "PUT": "medicine_catalog.edit_medicine",
    }
    serializer_class = AdminProductSerializer
    queryset = Product.objects.select_related("category", "brand")


class AdminInventoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsCatalogOps, HasMatrixPermission]
    required_matrix_permission = "inventory_warehouse.view_stock"
    serializer_class = AdminInventoryProductSerializer

    def get_queryset(self):
        queryset = Product.objects.select_related("category", "brand").order_by("name")
        status_value = self.request.query_params.get("stock_status", "").strip()
        if status_value:
            queryset = queryset.filter(stock_status=status_value)
        return queryset


class AdminInventoryDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsCatalogOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "inventory_warehouse.view_stock",
        "PATCH": "inventory_warehouse.update_stock",
        "PUT": "inventory_warehouse.update_stock",
    }
    serializer_class = AdminInventoryProductSerializer
    queryset = Product.objects.select_related("category", "brand")
