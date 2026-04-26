from django.urls import path

from .web_views import SuperAdminDashboardView, SuperAdminSectionView


urlpatterns = [
    path("dashboard/", SuperAdminDashboardView.as_view(), name="super-admin-dashboard"),
    path("dashboard/<slug:section_slug>/", SuperAdminSectionView.as_view(), name="super-admin-section"),
]
