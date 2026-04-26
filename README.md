# RakeshMed Platform

RakeshMed now has the initial full-stack layout for the production direction we agreed on:

- `apps/web`: `Next.js + TypeScript` storefront and back-office UI
- `apps/api`: `Django + Django REST Framework` API scaffold
- `PostgreSQL`: primary transactional database
- `Redis`: cache, OTP/session support, Celery broker/backend
- `Celery`: async job wiring for notifications, prescription workflows, and background processing

## Current structure

- `apps/web`
  - storefront, account, admin, pharmacist surfaces
- `apps/api`
  - Django settings split by environment
  - health endpoints under `/api/v1/health/`
  - Celery bootstrap
- `docker-compose.yml`
  - local Postgres, Redis, and API container

## Local development

1. Copy `.env.example` to `.env`
2. Start infrastructure:
   - `docker compose up -d postgres redis`
3. Create a Python virtual environment and install backend dependencies:
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate`
   - `pip install -r apps/api/requirements.txt`
4. Run Django migrations:
   - `python apps/api/manage.py migrate`
5. Start the API:
   - `python apps/api/manage.py runserver 0.0.0.0:8000`
6. Start the frontend:
   - `npm install`
   - `npm.cmd run dev:web`

## Useful URLs

- Frontend: `http://localhost:3000`
- API root: `http://localhost:8000/`
- Liveness check: `http://localhost:8000/api/v1/health/live/`
- Readiness check: `http://localhost:8000/api/v1/health/ready/`
- Django admin: `http://localhost:8000/admin/`

Local PostgreSQL defaults to host port `5433` to avoid conflicts with existing machine-level PostgreSQL installs.

## Root scripts

- `npm.cmd run dev:web`
- `npm.cmd run start:web`
- `npm.cmd run build:web`
- `npm.cmd run typecheck:web`
- `npm.cmd run lint:web`
- `npm.cmd run dev:api`
- `npm.cmd run migrate:api`
- `npm.cmd run check:api`
- `npm.cmd run check:migrations:api`
- `npm.cmd run test:api`
- `npm.cmd run test:e2e:web`
- `npm.cmd run test:e2e:web:smoke`
- `npm.cmd run test:e2e:web:ops`
- `npm.cmd run test:e2e:web:extended`
- `npm.cmd run preflight:prod`
- `npm.cmd run loadtest:api`
- `npm.cmd run verify`

## CI and release safety

- GitHub Actions CI is defined in [.github/workflows/ci.yml](C:/Users/00506686/RakeshMed/.github/workflows/ci.yml)
- Release checks are documented in [RELEASE_CHECKLIST.md](C:/Users/00506686/RakeshMed/RELEASE_CHECKLIST.md)
- Browser smoke and Playwright run order are documented in [BROWSER_SMOKE_CHECKLIST.md](C:/Users/00506686/RakeshMed/BROWSER_SMOKE_CHECKLIST.md)
- The repo now includes a starter env template in [.env.example](C:/Users/00506686/RakeshMed/.env.example)
- Production runtime and observability guidance are documented in [PRODUCTION_OPERATIONS.md](C:/Users/00506686/RakeshMed/PRODUCTION_OPERATIONS.md)
- Launch sequencing and pass/fail gates are documented in [LAUNCH_RUNBOOK.md](C:/Users/00506686/RakeshMed/LAUNCH_RUNBOOK.md)

## Production runtime

- `apps/web/Dockerfile` provides a real production frontend runtime using `next start`
- `apps/api/Dockerfile` now defaults to `gunicorn` instead of Django `runserver`
- `apps/api/gunicorn.conf.py` provides worker/thread/max-request tuning via env vars
- `docker-compose.production.yml` adds a production-shaped web + API + Celery worker + Celery beat stack
- `docker-compose.horizontal.yml` adds an optional multi-instance API + nginx overlay for horizontal-scale readiness
- `/api/v1/health/metrics/` exposes scrape-friendly request counters and response-time summaries
- `/api/v1/health/metrics.prom` exposes Prometheus-style text metrics
- `ops/prometheus-alerts.yml` includes starter production alert rules
- `ops/nginx/default.conf` includes a reverse-proxy baseline
- `ops/nginx/load-balanced.conf` includes a three-upstream nginx load-balancer baseline
- `scripts/backup_postgres.ps1` and `scripts/restore_postgres.ps1` provide backup/restore helpers
- `scripts/loadtest_api.py` provides a repeatable concurrent API load harness

## Recommended next backend modules

Build these next as real Django apps:

1. `users`
2. `catalog`
3. `inventory`
4. `prescriptions`
5. `cart`
6. `orders`
7. `payments`
8. `delivery`
9. `notifications`
10. `audit`
