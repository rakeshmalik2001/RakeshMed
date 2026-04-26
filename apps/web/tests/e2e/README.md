## E2E Coverage

This folder holds Playwright smoke coverage for launch-critical browser flows.

Current coverage:
- login and OTP verification
- customer search zero-state behavior
- checkout review and success flow with mocked live APIs
- account order payment refresh behavior
- customer prescription list and detail
- prescription upload submission
- admin inventory screen
- admin order operations
- admin order detail actions
- finance reconciliation and settlement detail
- pharmacist prescription queue
- pharmacist prescription detail review

Recommended local run order:
1. Start the API and web apps on their local ports.
2. Install web dependencies so Playwright is available.
3. Run `npm run test:e2e` from `apps/web` or `npm run test:e2e:web` from the repo root.

These tests rely on route interception so they validate browser behavior without requiring seeded demo state.
