from django.urls import path

from .web_views import ProcurementManagerDashboardView


urlpatterns = [
    path("dashboard/", ProcurementManagerDashboardView.as_view(), name="procurement-dashboard"),
]
