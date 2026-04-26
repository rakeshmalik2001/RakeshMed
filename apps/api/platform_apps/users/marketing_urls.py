from django.urls import path

from .web_views import MarketingManagerDashboardView


urlpatterns = [
    path("dashboard/", MarketingManagerDashboardView.as_view(), name="marketing-dashboard"),
]
