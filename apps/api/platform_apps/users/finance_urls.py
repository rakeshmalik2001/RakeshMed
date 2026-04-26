from django.urls import path

from .web_views import FinanceDashboardView


urlpatterns = [
    path("dashboard/", FinanceDashboardView.as_view(), name="finance-dashboard"),
]
