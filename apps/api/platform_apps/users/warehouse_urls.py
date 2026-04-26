from django.urls import path

from .web_views import WarehouseDashboardView


urlpatterns = [
    path("dashboard/", WarehouseDashboardView.as_view(), name="warehouse-dashboard"),
]
