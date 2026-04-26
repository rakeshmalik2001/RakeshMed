# Launch Runbook

Use this runbook for first production bring-up and every major release.

## 1. Configure production env

Set real values for:

- `NEXT_PUBLIC_API_BASE_URL`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `POSTGRES_*`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `PAYMENT_PROVIDER_*`
- `PAYMENT_WEBHOOK_SECRET`
- `METRICS_ACCESS_TOKEN`
- `PRESCRIPTION_STORAGE_BACKEND`
- `PRESCRIPTION_STORAGE_PUBLIC_BASE_URL`
- compliance and pharmacy license values

## 2. Start production stack

```powershell
docker compose -f docker-compose.production.yml up -d --build
```

Pass gate:

- frontend is served by the `web` service on port `3000`
- backend is served by the `api` service on port `8000`
- do not use `npm.cmd run dev:web` on the server
- API startup now runs `python manage.py migrate --noinput` automatically before Gunicorn boots

## 3. Run app preflight

```powershell
python .\scripts\preflight_production.py --base-url http://127.0.0.1:8000 --metrics-token YOUR_TOKEN
```

Pass gate:

- `required_env` passes
- `env_quality` passes
- `/api/v1/health/live/` returns `ok`
- `/api/v1/health/ready/` returns `ok`
- `/api/v1/health/metrics/` returns JSON metrics
- `/api/v1/health/metrics.prom` returns Prometheus text metrics

## 4. Run release verification

```powershell
npm.cmd run verify
```

Pass gate:

- no migration drift
- backend tests pass
- frontend typecheck/build pass

## 5. Run load test

```powershell
python .\scripts\loadtest_api.py --base-url http://127.0.0.1:8000 --requests 2000 --concurrency 100
```

Pass gate:

- success rate at or above 95%
- no sustained 5xx burst
- acceptable p95 and p99 latency for your SLA

## 6. Confirm metrics and alerts

- scrape `/api/v1/health/metrics.prom`
- load `ops/prometheus-alerts.yml`
- verify alert routing works

## 7. Backup and restore drill

```powershell
.\scripts\backup_postgres.ps1
.\scripts\restore_postgres.ps1 -BackupFile C:\path\to\backup.dump
```

Pass gate:

- backup file is created successfully
- restore completes in a rehearsal environment
- application starts cleanly after restore

## 8. Smoke test core flows

- run the browser automation layer:
  - `npm.cmd run test:e2e:web:smoke`
  - `npm.cmd run test:e2e:web:ops`
  - `npm.cmd run test:e2e:web:extended`
- use [BROWSER_SMOKE_CHECKLIST.md](C:/Users/00506686/RakeshMed/BROWSER_SMOKE_CHECKLIST.md) for the final manual browser pass
- customer login
- search
- product detail
- cart
- checkout
- payment session creation
- prescription upload
- admin dashboard
- pharmacist queue

## 9. Open traffic

Only open public traffic after all prior gates are green.
