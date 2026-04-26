from django.urls import path

from .web_views import VendorStaffDashboardView


urlpatterns = [
    path("dashboard/", VendorStaffDashboardView.as_view(), name="vendor-staff-dashboard"),
]
