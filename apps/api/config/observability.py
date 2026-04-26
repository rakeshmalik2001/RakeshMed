from __future__ import annotations

from django.core.cache import cache


METRIC_KEYS = {
    "request_total": "metrics:request_total",
    "duration_total_ms": "metrics:duration_total_ms",
    "status_2xx": "metrics:status:2xx",
    "status_4xx": "metrics:status:4xx",
    "status_5xx": "metrics:status:5xx",
    "cache_hit": "metrics:cache_hit",
    "cache_miss": "metrics:cache_miss",
    "idempotent_replay": "metrics:idempotent_replay",
}


def _safe_increment(key: str, amount: int = 1) -> None:
    if cache.add(key, amount, timeout=None):
        return
    try:
        cache.incr(key, amount)
    except ValueError:
        cache.set(key, amount, timeout=None)


def record_request_metrics(*, status_code: int, duration_ms: float, cache_status: str = "", replayed: bool = False) -> None:
    _safe_increment(METRIC_KEYS["request_total"])
    _safe_increment(METRIC_KEYS["duration_total_ms"], int(round(duration_ms)))

    if 200 <= status_code < 300:
        _safe_increment(METRIC_KEYS["status_2xx"])
    elif 400 <= status_code < 500:
        _safe_increment(METRIC_KEYS["status_4xx"])
    elif status_code >= 500:
        _safe_increment(METRIC_KEYS["status_5xx"])

    if cache_status == "HIT":
        _safe_increment(METRIC_KEYS["cache_hit"])
    elif cache_status == "MISS":
        _safe_increment(METRIC_KEYS["cache_miss"])

    if replayed:
        _safe_increment(METRIC_KEYS["idempotent_replay"])


def request_metrics_snapshot() -> dict[str, int | float]:
    total = int(cache.get(METRIC_KEYS["request_total"], 0) or 0)
    duration_total_ms = int(cache.get(METRIC_KEYS["duration_total_ms"], 0) or 0)
    cache_hits = int(cache.get(METRIC_KEYS["cache_hit"], 0) or 0)
    cache_misses = int(cache.get(METRIC_KEYS["cache_miss"], 0) or 0)
    cache_total = cache_hits + cache_misses

    return {
        "request_total": total,
        "duration_total_ms": duration_total_ms,
        "avg_duration_ms": round(duration_total_ms / total, 2) if total else 0,
        "status_2xx": int(cache.get(METRIC_KEYS["status_2xx"], 0) or 0),
        "status_4xx": int(cache.get(METRIC_KEYS["status_4xx"], 0) or 0),
        "status_5xx": int(cache.get(METRIC_KEYS["status_5xx"], 0) or 0),
        "cache_hit": cache_hits,
        "cache_miss": cache_misses,
        "cache_hit_ratio": round(cache_hits / cache_total, 4) if cache_total else 0,
        "idempotent_replay": int(cache.get(METRIC_KEYS["idempotent_replay"], 0) or 0),
    }
