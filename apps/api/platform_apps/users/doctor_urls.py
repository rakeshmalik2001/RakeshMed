from django.urls import path

from .web_views import DoctorDashboardView


urlpatterns = [
    path("dashboard/", DoctorDashboardView.as_view(), name="doctor-dashboard"),
]
