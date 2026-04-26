from django.db.models import Prefetch, Q
from rest_framework import generics
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from platform_apps.catalog.models import Product
from platform_apps.users.views import HasMatrixPermission

from .models import InventoryItem, StockLocation
from .serializers import InventoryAdjustmentSerializer, InventorySummarySerializer, StockLocationSerializer


class IsInventoryOps(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.role in {"admin", "catalog_manager", "warehouse_operator", "support_agent", "finance", "viewer"}
            )
        )


class AdminStockLocationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsInventoryOps, HasMatrixPermission]
    required_matrix_permission = "inventory_warehouse.view_stock"
    serializer_class = StockLocationSerializer
    queryset = StockLocation.objects.filter(is_active=True).order_by("sort_order", "name")


class AdminInventoryListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsInventoryOps, HasMatrixPermission]
    required_matrix_permission = "inventory_warehouse.view_stock"
    serializer_class = InventorySummarySerializer

    def get_queryset(self):
        queryset = (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "low_stock_rule",
                Prefetch(
                    "inventory_items",
                    queryset=InventoryItem.objects.select_related("location").order_by("location__sort_order", "location__name"),
                ),
            )
            .order_by("name")
        )
        stock_status = self.request.query_params.get("stock_status", "").strip()
        query = self.request.query_params.get("q", "").strip()
        if stock_status:
            queryset = queryset.filter(stock_status=stock_status)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
                | Q(manufacturer__icontains=query)
                | Q(category__name__icontains=query)
            )
        return queryset


class AdminInventoryDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsInventoryOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "inventory_warehouse.view_stock",
        "PATCH": "inventory_warehouse.update_stock",
        "PUT": "inventory_warehouse.update_stock",
    }

    def get_queryset(self):
        return (
            Product.objects.select_related("category", "brand")
            .prefetch_related(
                "low_stock_rule",
                Prefetch(
                    "inventory_items",
                    queryset=InventoryItem.objects.select_related("location").order_by("location__sort_order", "location__name"),
                ),
            )
            .order_by("name")
        )

    def get_serializer_class(self):
        if self.request.method in {"PATCH", "PUT"}:
            return InventoryAdjustmentSerializer
        return InventorySummarySerializer

    def patch(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        product.refresh_from_db()
        output = InventorySummarySerializer(product, context={"request": request})
        return Response(output.data)
