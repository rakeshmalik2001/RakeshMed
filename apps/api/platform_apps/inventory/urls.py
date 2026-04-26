from django.urls import path

from .views import AdminInventoryDetailView, AdminInventoryListView, AdminStockLocationListView


urlpatterns = [
    path("admin/locations/", AdminStockLocationListView.as_view(), name="admin-inventory-locations"),
    path("admin/items/", AdminInventoryListView.as_view(), name="admin-inventory-items"),
    path("admin/items/<int:pk>/", AdminInventoryDetailView.as_view(), name="admin-inventory-item-detail"),
]

