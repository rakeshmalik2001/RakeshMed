from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean


def build_url(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def request_once(base_url: str, path: str, timeout: float) -> tuple[int, float]:
    url = build_url(base_url, path)
    started = time.perf_counter()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception:
        status = 0
    duration_ms = (time.perf_counter() - started) * 1000
    return status, duration_ms


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return round(ordered[index], 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple concurrent API load tester")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        default=[],
        help="Endpoint path to hit. Can be passed multiple times.",
    )
    parser.add_argument("--requests", type=int, default=500, help="Total requests to perform")
    parser.add_argument("--concurrency", type=int, default=50, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds")
    args = parser.parse_args()

    paths = args.paths or [
        "/api/v1/catalog/products/",
        "/api/v1/catalog/products/?q=paracetamol",
        "/api/v1/delivery/serviceability/?pincode=400001",
        "/api/v1/health/live/",
    ]

    durations: list[float] = []
    statuses: dict[int, int] = {}
    started = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(request_once, args.base_url, paths[index % len(paths)], args.timeout)
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            status, duration_ms = future.result()
            durations.append(duration_ms)
            statuses[status] = statuses.get(status, 0) + 1

    elapsed = max(time.perf_counter() - started, 0.001)
    summary = {
        "base_url": args.base_url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_rps": round(args.requests / elapsed, 2),
        "success_rate": round(((statuses.get(200, 0) + statuses.get(201, 0)) / args.requests) * 100, 2),
        "avg_duration_ms": round(mean(durations), 2) if durations else 0,
        "p50_duration_ms": percentile(durations, 0.50),
        "p95_duration_ms": percentile(durations, 0.95),
        "p99_duration_ms": percentile(durations, 0.99),
        "statuses": statuses,
        "paths": paths,
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["success_rate"] >= 95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
