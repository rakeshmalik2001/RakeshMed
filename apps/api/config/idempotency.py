from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.http.request import RawPostDataException


class IdempotencyConflict(Exception):
    pass


class IdempotencyInProgress(Exception):
    pass


@dataclass
class IdempotencyRecord:
    state: str
    fingerprint: str
    value: dict | None = None


def _cache_key(*, namespace: str, user_id: int, idempotency_key: str) -> str:
    return f"idempotency:{namespace}:{user_id}:{idempotency_key}"


def _fingerprint(request) -> str:
    try:
        body = getattr(request, "body", b"") or b""
    except RawPostDataException:
        serialized = jsonable_request_data(request)
        body = serialized.encode("utf-8")
    digest = sha256()
    digest.update(request.method.encode("utf-8"))
    digest.update(b"|")
    digest.update(request.get_full_path().encode("utf-8"))
    digest.update(b"|")
    digest.update(body)
    return digest.hexdigest()


def jsonable_request_data(request) -> str:
    data = getattr(request, "data", {})
    if hasattr(data, "lists"):
        normalized = {key: value if len(value) > 1 else value[0] for key, value in data.lists()}
    else:
        normalized = data
    return str(normalized)


def begin_idempotent_request(*, request, namespace: str) -> tuple[str | None, IdempotencyRecord | None]:
    idempotency_key = str(request.headers.get("Idempotency-Key", "")).strip()
    if not idempotency_key:
        return None, None

    user_id = getattr(request.user, "pk", None)
    if not user_id:
        return None, None

    key = _cache_key(namespace=namespace, user_id=user_id, idempotency_key=idempotency_key)
    fingerprint = _fingerprint(request)
    pending_record = {"state": "pending", "fingerprint": fingerprint}
    created = cache.add(key, pending_record, timeout=settings.IDEMPOTENCY_PENDING_TTL_SECONDS)
    if created:
        return key, None

    cached = cache.get(key)
    if not cached:
        cache.set(key, pending_record, timeout=settings.IDEMPOTENCY_PENDING_TTL_SECONDS)
        return key, None

    cached_fingerprint = cached.get("fingerprint")
    if cached_fingerprint and cached_fingerprint != fingerprint:
        raise IdempotencyConflict("Idempotency-Key was reused with a different request payload.")

    state = cached.get("state")
    if state == "completed":
        return key, IdempotencyRecord(state=state, fingerprint=fingerprint, value=cached.get("value") or {})

    raise IdempotencyInProgress("Another matching request is already being processed.")


def complete_idempotent_request(*, cache_key: str | None, request, value: dict) -> None:
    if not cache_key:
        return
    cache.set(
        cache_key,
        {"state": "completed", "fingerprint": _fingerprint(request), "value": value},
        timeout=settings.IDEMPOTENCY_COMPLETED_TTL_SECONDS,
    )


def abort_idempotent_request(*, cache_key: str | None) -> None:
    if cache_key:
        cache.delete(cache_key)


def attach_idempotency_headers(response, *, replayed: bool) -> None:
    response["X-Idempotent-Replay"] = "true" if replayed else "false"
