from django.urls import path

from .web_views import AuditorDashboardView


urlpatterns = [
    path("dashboard/", AuditorDashboardView.as_view(), name="auditor-dashboard"),
]
