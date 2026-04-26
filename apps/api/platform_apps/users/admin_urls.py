from django.urls import path

from .web_views import AdminDashboardView


urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-role-dashboard"),
]
