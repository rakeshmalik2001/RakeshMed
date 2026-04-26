from django.urls import path

from .views import live_check, metrics_check, metrics_prometheus, ready_check


urlpatterns = [
    path("live/", live_check, name="health-live"),
    path("ready/", ready_check, name="health-ready"),
    path("metrics/", metrics_check, name="health-metrics"),
    path("metrics.prom", metrics_prometheus, name="health-metrics-prometheus"),
]
