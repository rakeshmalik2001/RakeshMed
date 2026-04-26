from django.urls import path

from .web_views import PharmacistDashboardView


urlpatterns = [
    path("dashboard/", PharmacistDashboardView.as_view(), name="pharmacist-dashboard"),
]
