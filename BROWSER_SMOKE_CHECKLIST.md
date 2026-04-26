# Browser Smoke Checklist

Use this checklist before any launch candidate or production release.

## 1. Start the local stack

- Start the API and supporting services.
- Start the web app on `http://localhost:3000`.
- Confirm the API is healthy:
  - `http://localhost:8000/api/v1/health/live/`
  - `http://localhost:8000/api/v1/health/ready/`

## 2. Run automated browser coverage

From the repo root:

```powershell
npm.cmd run test:e2e:web:smoke
npm.cmd run test:e2e:web:ops
npm.cmd run test:e2e:web:extended
```

If you prefer a single command:

```powershell
npm.cmd run test:e2e:web
```

Pass gate:

- no Playwright failures
- no unexpected browser console errors
- no route-level crashes

## 3. Run manual customer smoke

- Homepage loads and search bar is usable
- Search returns real zero-state when nothing matches
- Product detail loads for a real product
- Cart updates quantity correctly
- Checkout address, payment, review, and success pages load
- Success page shows the right payment status wording
- Account orders open and payment status can refresh
- Prescription upload works and account prescription detail opens

## 4. Run manual ops smoke

- Admin dashboard loads
- Admin orders filters work
- Admin order detail opens
- Inventory screen loads
- Reconciliation and settlements screens load
- Pharmacist queue filters work
- Pharmacist prescription detail opens
- Pharmacist review actions render correctly

## 5. Final browser release gate

Only continue to deployment when:

- automated browser suite is green
- customer manual smoke is green
- ops manual smoke is green
- backend checks and build checks are already green
