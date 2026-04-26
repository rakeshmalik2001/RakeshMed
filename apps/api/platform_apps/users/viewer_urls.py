from django.urls import path

from .web_views import ViewerDashboardView


urlpatterns = [
    path("dashboard/", ViewerDashboardView.as_view(), name="viewer-dashboard"),
]
