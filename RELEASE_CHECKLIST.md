# Release Checklist

Use this checklist before shipping a release candidate.

## Backend

- `npm run check:api`
- `npm run check:migrations:api`
- `npm run test:api`
- Confirm `/api/v1/health/live/` returns `200`
- Confirm `/api/v1/health/ready/` reports all expected dependencies as healthy

## Frontend

- `npm run typecheck:web`
- `npm run build:web`
- `npm run test:e2e:web:smoke`
- `npm run test:e2e:web:ops`
- Verify login, account, checkout, admin, and pharmacist routes locally
- Use [BROWSER_SMOKE_CHECKLIST.md](C:/Users/00506686/RakeshMed/BROWSER_SMOKE_CHECKLIST.md) for the final manual/browser gate

## Config

- Production secrets are provided through environment variables, not source control
- `DJANGO_ALLOWED_HOSTS`, CORS, CSRF trusted origins, and HTTPS cookie settings match production
- Payment and webhook secrets are rotated and current

## Release Gate

- CI is green on the target branch
- No migration drift remains
- No known auth/session regressions remain
- No readiness check regressions remain
- Browser smoke is green for customer and ops flows
