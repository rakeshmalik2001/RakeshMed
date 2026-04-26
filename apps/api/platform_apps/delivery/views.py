from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api_resilience import build_cached_response
from config.throttles import PublicServiceabilityThrottle
from platform_apps.users.views import HasMatrixPermission

from .models import DeliveryShipment, DeliveryZone
from .serializers import (
    DeliveryShipmentSerializer,
    DeliveryShipmentUpdateSerializer,
    DeliveryZoneSerializer,
    ServiceabilitySerializer,
)
from .services import apply_delivery_shipment_update, ensure_delivery_zones_seeded, is_dispatch_ready, serviceability_snapshot


class IsDeliveryOps(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.role in {"admin", "warehouse_operator", "support_agent", "finance", "viewer"}
            )
        )


class DeliveryServiceabilityView(APIView):
    permission_classes = []
    throttle_classes = [PublicServiceabilityThrottle]

    def get_permissions(self):
        return []

    def get(self, request):
        pincode = str(request.query_params.get("pincode", "")).strip()
        return build_cached_response(
            request,
            prefix="delivery:serviceability",
            timeout=settings.SERVICEABILITY_CACHE_TTL_SECONDS,
            payload_factory=lambda: ServiceabilitySerializer(serviceability_snapshot(pincode)).data,
        )


class AdminDeliveryZoneListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDeliveryOps, HasMatrixPermission]
    required_matrix_permission = "orders.view_orders"
    serializer_class = DeliveryZoneSerializer

    def get_queryset(self):
        ensure_delivery_zones_seeded()
        return DeliveryZone.objects.filter(is_active=True).order_by("pincode_prefix", "name")


class AdminDeliveryShipmentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDeliveryOps, HasMatrixPermission]
    required_matrix_permission = "orders.view_orders"
    serializer_class = DeliveryShipmentSerializer

    def get_queryset(self):
        ensure_delivery_zones_seeded()
        queryset = DeliveryShipment.objects.select_related("order", "zone").prefetch_related("events", "events__created_by").order_by("-updated_at")
        status_value = self.request.query_params.get("status", "").strip()
        ready_only = self.request.query_params.get("ready", "").strip().lower()
        if status_value:
            queryset = queryset.filter(status=status_value)
        if ready_only in {"1", "true", "yes"}:
            shipment_ids = [shipment.id for shipment in queryset if is_dispatch_ready(shipment.order, zone=shipment.zone)]
            queryset = queryset.filter(id__in=shipment_ids)
        return queryset


class AdminDeliveryShipmentDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsDeliveryOps, HasMatrixPermission]
    matrix_permission_map = {
        "GET": "orders.view_orders",
        "PATCH": "orders.process_order",
        "PUT": "orders.process_order",
    }
    lookup_field = "order__order_number"
    lookup_url_kwarg = "order_number"

    def get_queryset(self):
        ensure_delivery_zones_seeded()
        return DeliveryShipment.objects.select_related("order", "zone").prefetch_related("events", "events__created_by")

    def get_object(self):
        return generics.get_object_or_404(self.get_queryset(), order__order_number=self.kwargs["order_number"])

    def get_serializer_class(self):
        if self.request.method in {"PATCH", "PUT"}:
            return DeliveryShipmentUpdateSerializer
        return DeliveryShipmentSerializer

    def patch(self, request, *args, **kwargs):
        shipment = self.get_object()
        serializer = self.get_serializer(shipment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        shipment = apply_delivery_shipment_update(shipment, actor=request.user, **serializer.validated_data)
        output = DeliveryShipmentSerializer(shipment)
        return Response(output.data)
