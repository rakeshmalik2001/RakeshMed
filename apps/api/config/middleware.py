import logging
import time
import uuid

from config.observability import record_request_metrics


request_logger = logging.getLogger("rakeshmed.request")


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("X-Frame-Options", "DENY")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' https://cdn.jsdelivr.net; connect-src 'self' https://cdn.jsdelivr.net http://localhost:3000 http://localhost:8000 http://localhost:8080; "
            "font-src 'self' data: https://cdn.jsdelivr.net; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        return response


class ApiVersionHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("X-API-Version", "v1")
        response.setdefault("X-API-Supported-Versions", "v1")
        response.setdefault(
            "X-API-Deprecation-Policy",
            "Additive changes may ship within v1; breaking changes require a new versioned path.",
        )
        return response


class StructuredRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id
        started_at = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        content_length = response.headers.get("Content-Length", "")
        if not content_length:
            rendered_content = getattr(response, "content", b"")
            content_length = len(rendered_content) if rendered_content else 0
        cache_status = response.headers.get("X-Cache", "")
        user_role = getattr(getattr(request, "user", None), "role", "anonymous")
        replayed = response.headers.get("X-Idempotent-Replay", "").lower() == "true"
        response.setdefault("X-Request-ID", request_id)
        response.setdefault("X-Response-Time-Ms", str(duration_ms))
        record_request_metrics(
            status_code=response.status_code,
            duration_ms=duration_ms,
            cache_status=cache_status,
            replayed=replayed,
        )
        request_logger.info(
            "request.complete method=%s path=%s status=%s duration_ms=%s bytes=%s cache=%s user_role=%s request_id=%s",
            request.method,
            request.get_full_path(),
            response.status_code,
            duration_ms,
            content_length,
            cache_status or "none",
            user_role,
            request_id,
        )
        return response
