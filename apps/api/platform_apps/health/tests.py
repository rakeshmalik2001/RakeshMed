from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient


class HealthEndpointTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()

    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_HEALTH_ENDPOINTS", True)
    @patch("platform_apps.health.views._ping_redis_service", return_value="ok")
    def test_ready_check_reports_broker_and_result_backend(self, _ping_redis_service) -> None:
        response = self.client.get("/api/v1/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["checks"]["database"], "ok")
        self.assertEqual(response.data["checks"]["cache"], "ok")
        self.assertIn(response.data["checks"]["broker"], {"ok", "skipped"})
        self.assertIn(response.data["checks"]["result_backend"], {"ok", "skipped"})

    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_HEALTH_ENDPOINTS", True)
    @patch("platform_apps.health.views._ping_redis_service", side_effect=RuntimeError("redis down"))
    def test_ready_check_degrades_when_broker_check_fails(self, _ping_redis_service) -> None:
        response = self.client.get("/api/v1/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "degraded")
        self.assertEqual(response.data["checks"]["broker"], "error")
        self.assertEqual(response.data["checks"]["result_backend"], "error")

    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_HEALTH_ENDPOINTS", True)
    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_METRICS_ENDPOINTS", True)
    @patch("platform_apps.health.views.settings.METRICS_ACCESS_TOKEN", "")
    def test_metrics_endpoint_exposes_request_counters(self) -> None:
        self.client.get("/api/v1/health/live/")

        response = self.client.get("/api/v1/health/metrics/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("metrics", response.data)
        self.assertGreaterEqual(response.data["metrics"]["request_total"], 1)

    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_HEALTH_ENDPOINTS", True)
    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_METRICS_ENDPOINTS", True)
    @patch("platform_apps.health.views.settings.METRICS_ACCESS_TOKEN", "")
    def test_prometheus_metrics_endpoint_renders_text_payload(self) -> None:
        self.client.get("/api/v1/health/live/")

        response = self.client.get("/api/v1/health/metrics.prom")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers["Content-Type"])
        self.assertIn("rakeshmed_request_total", response.content.decode("utf-8"))

    @patch("platform_apps.health.views.settings.METRICS_ACCESS_TOKEN", "secret-token")
    def test_metrics_endpoint_requires_token_when_configured(self) -> None:
        unauthorized = self.client.get("/api/v1/health/metrics/")
        authorized = self.client.get("/api/v1/health/metrics/", HTTP_X_METRICS_TOKEN="secret-token")

        self.assertEqual(unauthorized.status_code, 403)
        self.assertEqual(authorized.status_code, 200)

    @patch("platform_apps.health.views.settings.ALLOW_PUBLIC_HEALTH_ENDPOINTS", False)
    @patch("platform_apps.health.views.settings.HEALTHCHECK_ACCESS_TOKEN", "health-secret")
    def test_health_endpoints_require_token_when_public_access_disabled(self) -> None:
        unauthorized = self.client.get("/api/v1/health/live/")
        authorized = self.client.get("/api/v1/health/live/", HTTP_X_HEALTH_TOKEN="health-secret")

        self.assertEqual(unauthorized.status_code, 403)
        self.assertEqual(authorized.status_code, 200)
