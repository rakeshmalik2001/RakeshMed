from django.urls import path

from .web_views import CatalogManagerDashboardView


urlpatterns = [
    path("dashboard/", CatalogManagerDashboardView.as_view(), name="catalog-dashboard"),
]
