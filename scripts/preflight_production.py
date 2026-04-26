from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


REQUIRED_ENV_VARS = [
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "PAYMENT_PROVIDER_NAME",
    "PAYMENT_PROVIDER_PUBLIC_KEY",
    "PAYMENT_PROVIDER_SECRET_KEY",
    "PAYMENT_WEBHOOK_SECRET",
    "METRICS_ACCESS_TOKEN",
    "PRESCRIPTION_STORAGE_BACKEND",
    "PRESCRIPTION_STORAGE_PUBLIC_BASE_URL",
]

PLACEHOLDER_SUBSTRINGS = (
    "change-me",
    "replace-with",
    "local-prod",
    "tc_test_",
    "simulated_gateway",
)


def load_dotenv_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name or os.getenv(name):
                continue
            os.environ[name] = value


def fetch_json(url: str, *, metrics_token: str = "") -> tuple[bool, dict | str]:
    request = urllib.request.Request(url)
    if metrics_token:
        request.add_header("X-Metrics-Token", metrics_token)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = response.read().decode("utf-8")
            return True, json.loads(payload)
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)


def fetch_text(url: str, *, metrics_token: str = "") -> tuple[bool, str]:
    request = urllib.request.Request(url)
    if metrics_token:
        request.add_header("X-Metrics-Token", metrics_token)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return True, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)


def validate_env_values() -> list[str]:
    issues: list[str] = []

    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name, "").strip()
        lowered = value.lower()
        if any(marker in lowered for marker in PLACEHOLDER_SUBSTRINGS):
            issues.append(f"{name} still looks like a placeholder")

    webhook_secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
    if "@" in webhook_secret:
        issues.append("PAYMENT_WEBHOOK_SECRET looks like an email address, not a webhook secret")
    if webhook_secret and len(webhook_secret) < 12:
        issues.append("PAYMENT_WEBHOOK_SECRET is unusually short")

    metrics_token = os.getenv("METRICS_ACCESS_TOKEN", "").strip()
    if metrics_token and len(metrics_token) < 16:
        issues.append("METRICS_ACCESS_TOKEN is unusually short")

    payment_provider = os.getenv("PAYMENT_PROVIDER_NAME", "").strip().lower()
    payment_public_key = os.getenv("PAYMENT_PROVIDER_PUBLIC_KEY", "").strip()
    if payment_provider == "razorpay" and not payment_public_key.startswith(("rzp_test_", "rzp_live_")):
        issues.append("PAYMENT_PROVIDER_PUBLIC_KEY does not look like a Razorpay key id")

    return issues


def main() -> int:
    load_dotenv_file()

    parser = argparse.ArgumentParser(description="Production launch preflight checks")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the deployed API")
    parser.add_argument(
        "--metrics-token",
        default=os.getenv("METRICS_ACCESS_TOKEN", ""),
        help="Metrics token for protected metrics endpoints",
    )
    args = parser.parse_args()

    results: list[tuple[str, bool, str]] = []

    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name, "").strip()]
    if missing:
        results.append(("required_env", False, f"Missing env vars: {', '.join(missing)}"))
    else:
        results.append(("required_env", True, "All required env vars are present"))

    env_issues = validate_env_values()
    if env_issues:
        results.append(("env_quality", False, "; ".join(env_issues)))
    else:
        results.append(("env_quality", True, "Environment values look non-placeholder and production-ready"))

    live_ok, live_payload = fetch_json(f"{args.base_url.rstrip('/')}/api/v1/health/live/")
    results.append(
        (
            "health_live",
            live_ok and isinstance(live_payload, dict) and live_payload.get("status") == "ok",
            str(live_payload),
        )
    )

    ready_ok, ready_payload = fetch_json(f"{args.base_url.rstrip('/')}/api/v1/health/ready/")
    ready_pass = ready_ok and isinstance(ready_payload, dict) and ready_payload.get("status") == "ok"
    results.append(("health_ready", ready_pass, str(ready_payload)))

    metrics_ok, metrics_payload = fetch_json(
        f"{args.base_url.rstrip('/')}/api/v1/health/metrics/",
        metrics_token=args.metrics_token,
    )
    metrics_pass = metrics_ok and isinstance(metrics_payload, dict) and "metrics" in metrics_payload
    results.append(("health_metrics_json", metrics_pass, str(metrics_payload)))

    prom_ok, prom_payload = fetch_text(
        f"{args.base_url.rstrip('/')}/api/v1/health/metrics.prom",
        metrics_token=args.metrics_token,
    )
    prom_pass = prom_ok and "rakeshmed_request_total" in prom_payload
    results.append(("health_metrics_prom", prom_pass, prom_payload[:200]))

    failed = [name for name, ok, _detail in results if not ok]
    for name, ok, detail in results:
        state = "PASS" if ok else "FAIL"
        print(f"[{state}] {name}: {detail}")

    if failed:
        print(f"\nPreflight failed: {', '.join(failed)}")
        return 1

    print("\nPreflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
