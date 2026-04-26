from django.urls import path

from .web_views import OperationsManagerDashboardView


urlpatterns = [
    path("dashboard/", OperationsManagerDashboardView.as_view(), name="operations-dashboard"),
]
