from __future__ import annotations

from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.utils.cache import patch_cache_control, patch_vary_headers
from rest_framework import generics
from rest_framework.response import Response


def _cache_key(prefix: str, request, vary_by_user: bool = False) -> str:
    actor = "anon"
    if vary_by_user and getattr(request, "user", None) and request.user.is_authenticated:
        actor = f"user:{request.user.pk}"
    digest = sha256(f"{prefix}|{actor}|{request.get_full_path()}".encode("utf-8")).hexdigest()
    return f"api-resilience:{digest}"


def build_cached_response(
    request,
    *,
    prefix: str,
    timeout: int,
    payload_factory,
    vary_by_user: bool = False,
    is_public: bool = True,
):
    key = _cache_key(prefix, request, vary_by_user=vary_by_user)
    payload = cache.get(key)
    cache_hit = payload is not None
    if payload is None:
        payload = payload_factory()
        cache.set(key, payload, timeout=timeout)

    response = Response(payload)
    response["X-Cache"] = "HIT" if cache_hit else "MISS"
    patch_cache_control(
        response,
        public=is_public,
        private=not is_public,
        max_age=timeout,
        stale_while_revalidate=max(1, timeout // 2),
        stale_if_error=max(timeout * 5, timeout),
    )
    if vary_by_user:
        patch_vary_headers(response, ["Authorization"])
    return response


class CachedListAPIView(generics.ListAPIView):
    cache_prefix = "list"
    cache_timeout = settings.PUBLIC_API_CACHE_TTL_SECONDS
    cache_vary_by_user = False
    cache_is_public = True

    def get_cache_prefix(self) -> str:
        return self.cache_prefix

    def get_cache_timeout(self) -> int:
        return self.cache_timeout

    def list(self, request, *args, **kwargs):
        return build_cached_response(
            request,
            prefix=self.get_cache_prefix(),
            timeout=self.get_cache_timeout(),
            vary_by_user=self.cache_vary_by_user,
            is_public=self.cache_is_public,
            payload_factory=lambda: self.get_serializer(self.filter_queryset(self.get_queryset()), many=True).data,
        )


class CachedRetrieveAPIView(generics.RetrieveAPIView):
    cache_prefix = "detail"
    cache_timeout = settings.PUBLIC_API_CACHE_TTL_SECONDS
    cache_vary_by_user = False
    cache_is_public = True

    def get_cache_prefix(self) -> str:
        return self.cache_prefix

    def get_cache_timeout(self) -> int:
        return self.cache_timeout

    def retrieve(self, request, *args, **kwargs):
        return build_cached_response(
            request,
            prefix=self.get_cache_prefix(),
            timeout=self.get_cache_timeout(),
            vary_by_user=self.cache_vary_by_user,
            is_public=self.cache_is_public,
            payload_factory=lambda: self.get_serializer(self.get_object()).data,
        )
