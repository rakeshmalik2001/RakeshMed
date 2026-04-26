from django.urls import path

from .web_views import VendorDashboardView


urlpatterns = [
    path("dashboard/", VendorDashboardView.as_view(), name="vendor-dashboard"),
]
