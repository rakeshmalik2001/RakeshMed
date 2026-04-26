from django.urls import path

from .web_views import SecurityAdminDashboardView


urlpatterns = [
    path("dashboard/", SecurityAdminDashboardView.as_view(), name="security-dashboard"),
]
