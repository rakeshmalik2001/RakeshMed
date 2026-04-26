from django.urls import path

from .web_views import ComplianceOfficerDashboardView


urlpatterns = [
    path("dashboard/", ComplianceOfficerDashboardView.as_view(), name="compliance-dashboard"),
]
