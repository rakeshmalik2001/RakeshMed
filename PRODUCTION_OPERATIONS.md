# Production Operations

This repo now includes the application-side pieces needed for a serious production rollout:

- `apps/web/Dockerfile` for a production Next.js runtime using `next start`
- `apps/api/gunicorn.conf.py` for tuned multi-worker API serving
- `docker-compose.production.yml` for web + API + Celery worker + Celery beat runtime shape
- `docker-compose.horizontal.yml` for a multi-instance API overlay with nginx in front
- `/api/v1/health/metrics/` for scrape-friendly runtime counters
- `/api/v1/health/metrics.prom` for Prometheus text scraping
- `scripts/loadtest_api.py` for repeatable API load exercises
- `ops/prometheus-alerts.yml` for starter alert thresholds
- `ops/nginx/default.conf` for reverse-proxy baseline
- `ops/nginx/load-balanced.conf` for multi-instance API load balancing
- `scripts/backup_postgres.ps1` and `scripts/restore_postgres.ps1` for restore drills

## Recommended rollout order

1. Set real production values in `.env`
2. Run migrations
3. Start `web`, `postgres`, `redis`, `api`, `celery-worker`, and `celery-beat`
4. Confirm `/api/v1/health/live/`, `/api/v1/health/ready/`, and `/api/v1/health/metrics/`
5. Run load tests against public read endpoints before opening traffic
6. Wire metrics scraping and alerts
7. Perform a backup and restore drill before launch

## Horizontal scaling and load balancing

For a single-node baseline, keep using `docker-compose.production.yml`.

For a multi-instance API shape on one host, start with:

```powershell
docker compose -f docker-compose.production.yml -f docker-compose.horizontal.yml up -d --build
```

This adds:

- `api-a`
- `api-b`
- `api-c`
- `nginx` on port `8080`

That is not the same as a cloud autoscaling group, but it gives you a real repo-level path for:

- multiple API instances
- nginx upstream balancing
- failover between app containers

## Read replica readiness

The backend now supports an optional replica connection through:

- `POSTGRES_REPLICA_*`
- `ENABLE_DB_REPLICA_ROUTING`

Behavior:

- writes always stay on `default`
- migrations always stay on `default`
- reads can go to `replica` when routing is enabled
- transactional work stays pinned to primary

Turn this on only after your replica lag and consistency behavior are understood.

## Gunicorn baseline

- `GUNICORN_WORKERS=9`
- `GUNICORN_THREADS=4`
- `GUNICORN_TIMEOUT=60`
- `GUNICORN_MAX_REQUESTS=2000`
- `GUNICORN_MAX_REQUESTS_JITTER=200`

Tune these with actual CPU, memory, and p95 latency numbers from your servers.

## Celery baseline

- `CELERY_WORKER_CONCURRENCY=4`
- Separate workers from the API process
- Keep broker and result backend on Redis

## Metrics

Use `/api/v1/health/metrics/` for:

- total requests
- average response time
- 2xx / 4xx / 5xx counters
- cache hit ratio
- idempotent replay count

## Load test example

```powershell
python .\scripts\loadtest_api.py --base-url http://127.0.0.1:8000 --requests 2000 --concurrency 100
```

## Prescription file delivery

For production, point prescription files at object storage or a CDN-backed origin by setting:

- `PRESCRIPTION_STORAGE_BACKEND`
- `PRESCRIPTION_STORAGE_PUBLIC_BASE_URL`
- `PRESCRIPTION_STORAGE_BUCKET`
- `PRESCRIPTION_STORAGE_REGION`
- `PRESCRIPTION_STORAGE_ENDPOINT`
- `PRESCRIPTION_STORAGE_CDN_DOMAIN`

If `default_storage.url()` is available, the API will use it automatically. Otherwise it can build public URLs from the configured base URL.
