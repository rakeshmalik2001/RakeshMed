from django.urls import path

from .views import (
    AdminDeliveryShipmentDetailView,
    AdminDeliveryShipmentListView,
    AdminDeliveryZoneListView,
    DeliveryServiceabilityView,
)


urlpatterns = [
    path("serviceability/", DeliveryServiceabilityView.as_view(), name="delivery-serviceability"),
    path("admin/zones/", AdminDeliveryZoneListView.as_view(), name="delivery-admin-zones"),
    path("admin/shipments/", AdminDeliveryShipmentListView.as_view(), name="delivery-admin-shipments"),
    path("admin/shipments/<str:order_number>/", AdminDeliveryShipmentDetailView.as_view(), name="delivery-admin-shipment-detail"),
]
