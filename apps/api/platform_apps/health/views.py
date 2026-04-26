from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.db.utils import OperationalError
from hmac import compare_digest
from redis import Redis
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from config.observability import request_metrics_snapshot


def _ping_redis_service(url: str) -> str:
    if not url or not url.startswith("redis://"):
        return "skipped"

    client = Redis.from_url(
        url,
        socket_connect_timeout=1,
        socket_timeout=1,
        retry_on_timeout=False,
    )
    try:
        client.ping()
    finally:
        client.close()
    return "ok"


def _has_valid_token(request, *, expected_token: str, header_name: str, allow_public: bool) -> bool:
    if expected_token:
        provided = request.headers.get(header_name, "").strip()
        return bool(provided) and compare_digest(provided, expected_token)
    return allow_public


def _health_access_denied():
    return Response({"detail": "Unauthorized health endpoint access."}, status=status.HTTP_403_FORBIDDEN)


@api_view(["GET"])
@permission_classes([AllowAny])
def live_check(_request):
    if not _has_valid_token(
        _request,
        expected_token=(getattr(settings, "HEALTHCHECK_ACCESS_TOKEN", "") or "").strip(),
        header_name="X-Health-Token",
        allow_public=bool(getattr(settings, "ALLOW_PUBLIC_HEALTH_ENDPOINTS", False)),
    ):
        return _health_access_denied()
    return Response(
        {
            "status": "ok",
            "service": "rakeshmed-api",
            "environment": "development" if settings.DEBUG else "production"
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def ready_check(_request):
    if not _has_valid_token(
        _request,
        expected_token=(getattr(settings, "HEALTHCHECK_ACCESS_TOKEN", "") or "").strip(),
        header_name="X-Health-Token",
        allow_public=bool(getattr(settings, "ALLOW_PUBLIC_HEALTH_ENDPOINTS", False)),
    ):
        return _health_access_denied()
    checks = {"database": "ok", "cache": "ok", "broker": "ok", "result_backend": "ok"}
    response_status = status.HTTP_200_OK

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        checks["database"] = "error"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        cache.set("healthcheck", "ok", timeout=5)
        if cache.get("healthcheck") != "ok":
            raise RuntimeError("cache_readback_failed")
    except Exception:
        checks["cache"] = "error"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        checks["broker"] = _ping_redis_service(settings.CELERY_BROKER_URL)
    except Exception:
        checks["broker"] = "error"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        checks["result_backend"] = _ping_redis_service(settings.CELERY_RESULT_BACKEND)
    except Exception:
        checks["result_backend"] = "error"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        {
            "status": "ok" if response_status == status.HTTP_200_OK else "degraded",
            "service": "rakeshmed-api",
            "checks": checks
        },
        status=response_status
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def metrics_check(request):
    if not _has_valid_token(
        request,
        expected_token=(getattr(settings, "METRICS_ACCESS_TOKEN", "") or "").strip(),
        header_name="X-Metrics-Token",
        allow_public=bool(getattr(settings, "ALLOW_PUBLIC_METRICS_ENDPOINTS", False)),
    ):
        return Response({"detail": "Unauthorized metrics access."}, status=status.HTTP_403_FORBIDDEN)

    metrics = request_metrics_snapshot()
    return Response(
        {
            "service": "rakeshmed-api",
            "environment": "development" if settings.DEBUG else "production",
            "metrics": metrics,
            "checks": {
                "database": "ok",
                "cache": "ok",
            },
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def metrics_prometheus(request):
    if not _has_valid_token(
        request,
        expected_token=(getattr(settings, "METRICS_ACCESS_TOKEN", "") or "").strip(),
        header_name="X-Metrics-Token",
        allow_public=bool(getattr(settings, "ALLOW_PUBLIC_METRICS_ENDPOINTS", False)),
    ):
        return Response({"detail": "Unauthorized metrics access."}, status=status.HTTP_403_FORBIDDEN)

    metrics = request_metrics_snapshot()
    lines = [
        "# TYPE rakeshmed_request_total counter",
        f"rakeshmed_request_total {metrics['request_total']}",
        "# TYPE rakeshmed_duration_total_ms counter",
        f"rakeshmed_duration_total_ms {metrics['duration_total_ms']}",
        "# TYPE rakeshmed_avg_duration_ms gauge",
        f"rakeshmed_avg_duration_ms {metrics['avg_duration_ms']}",
        "# TYPE rakeshmed_status_2xx_total counter",
        f"rakeshmed_status_2xx_total {metrics['status_2xx']}",
        "# TYPE rakeshmed_status_4xx_total counter",
        f"rakeshmed_status_4xx_total {metrics['status_4xx']}",
        "# TYPE rakeshmed_status_5xx_total counter",
        f"rakeshmed_status_5xx_total {metrics['status_5xx']}",
        "# TYPE rakeshmed_cache_hit_total counter",
        f"rakeshmed_cache_hit_total {metrics['cache_hit']}",
        "# TYPE rakeshmed_cache_miss_total counter",
        f"rakeshmed_cache_miss_total {metrics['cache_miss']}",
        "# TYPE rakeshmed_cache_hit_ratio gauge",
        f"rakeshmed_cache_hit_ratio {metrics['cache_hit_ratio']}",
        "# TYPE rakeshmed_idempotent_replay_total counter",
        f"rakeshmed_idempotent_replay_total {metrics['idempotent_replay']}",
    ]
    from django.http import HttpResponse

    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; version=0.0.4; charset=utf-8")
