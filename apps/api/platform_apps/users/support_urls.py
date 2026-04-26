from django.urls import path

from .web_views import SupportDashboardView


urlpatterns = [
    path("dashboard/", SupportDashboardView.as_view(), name="support-dashboard"),
]
