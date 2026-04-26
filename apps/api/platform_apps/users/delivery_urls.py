from django.urls import path

from .web_views import DeliveryDashboardView


urlpatterns = [
    path("dashboard/", DeliveryDashboardView.as_view(), name="delivery-dashboard"),
]
