# RakeshMed Production Readiness Checklist

This checklist is for turning the current repository into a real, launch-ready, scalable medicine platform.

## 1. Core Architecture

- [x] Frontend app scaffold exists in `apps/web`
- [x] Backend API scaffold exists in `apps/api`
- [x] Local `PostgreSQL + Redis + API` docker compose exists
- [ ] Create real Django apps:
  - [ ] `users`
  - [ ] `catalog`
  - [ ] `inventory`
  - [ ] `prescriptions`
  - [ ] `cart`
  - [ ] `orders`
  - [ ] `payments`
  - [ ] `delivery`
  - [ ] `notifications`
  - [ ] `audit`
- [ ] Define clear ownership and boundaries between modules
- [ ] Add API versioning and deprecation rules

## 2. Database and Data Integrity

- [ ] Create PostgreSQL schema for all core entities
- [ ] Add Django migrations for all modules
- [ ] Add unique constraints for business-critical identifiers
- [ ] Add foreign key relationships and delete/update rules
- [ ] Add indexes for:
  - [ ] search fields
  - [ ] order lookups
  - [ ] prescription status
  - [ ] inventory availability
  - [ ] pincode serviceability
- [ ] Add audit fields:
  - [ ] `created_at`
  - [ ] `updated_at`
  - [ ] `created_by`
  - [ ] `updated_by`
- [ ] Add soft-delete strategy where required
- [ ] Define data retention policy for prescriptions and invoices
- [ ] Define backup and restore process for PostgreSQL
- [ ] Test backup restore in a non-production environment

## 3. Authentication and Authorization

- [ ] Implement OTP send API
- [ ] Implement OTP verify API
- [ ] Add login/session/token lifecycle rules
- [ ] Define role-based access control
- [ ] Add roles:
  - [ ] `customer`
  - [ ] `admin`
  - [ ] `catalog_manager`
  - [ ] `pharmacist`
  - [ ] `warehouse_operator`
  - [ ] `support_agent`
  - [ ] `finance`
- [ ] Protect admin routes by permission
- [ ] Protect pharmacist routes by permission
- [ ] Rate-limit auth APIs
- [ ] Add lockout / brute-force protection
- [ ] Add session expiry and revocation rules

## 4. Catalog and Search

- [ ] Build real category API
- [ ] Build real product listing API
- [ ] Build real product detail API
- [ ] Add brand and salt mapping
- [ ] Add substitute medicine relationships
- [ ] Add out-of-stock fallback logic
- [ ] Add pincode-aware availability logic
- [ ] Add product status controls: draft / active / blocked / unavailable
- [ ] Add search endpoint
- [ ] Add typo tolerance and synonym support
- [ ] Add OpenSearch integration for scale phase

## 5. Prescription Workflow

- [ ] Build prescription upload API
- [ ] Store uploaded files in private object storage
- [ ] Add pharmacist review queue
- [ ] Add approved / rejected / pending / clarification states
- [ ] Add substitution workflow
- [ ] Add prescription-to-order linking
- [ ] Add review notes and reviewer audit trail
- [ ] Add prescription expiry rules
- [ ] Add signed URL access for private documents
- [ ] Add SLA monitoring for prescription review turnaround

## 6. Cart, Checkout, Orders, and Payments

- [ ] Replace mock cart state with backend cart APIs
- [ ] Build checkout validation API
- [ ] Build order placement API
- [ ] Build order history and detail APIs
- [ ] Add order status machine
- [ ] Add delivery fee and tax calculation rules
- [ ] Add prescription-required validation before order placement
- [ ] Integrate payment gateway
- [ ] Add payment webhook verification
- [ ] Add refund workflow
- [ ] Add invoice generation

## 7. Inventory and Fulfillment

- [ ] Build inventory module
- [ ] Add stock by warehouse
- [ ] Add reserved stock logic
- [ ] Add batch tracking
- [ ] Add expiry tracking
- [ ] Add near-expiry alerting
- [ ] Add pincode serviceability mapping
- [ ] Add order-to-warehouse allocation rules
- [ ] Add shipment status integration

## 8. Frontend Integration

- [ ] Replace mock frontend catalog data with live APIs
- [ ] Replace mock search data with live APIs
- [ ] Replace mock cart state with live APIs
- [ ] Replace mock prescription flow with live APIs
- [ ] Replace mock order data with live APIs
- [ ] Add API error handling and retry states
- [ ] Add skeleton/loading states
- [ ] Add empty states and degraded states
- [ ] Add centralized API client and auth handling

## 9. Responsiveness and Mobile Experience

- [ ] Audit every major page on mobile widths
- [ ] Audit every major page on tablet widths
- [ ] Ensure header and navigation work on touch devices
- [ ] Ensure category navigation is usable on mobile
- [ ] Ensure cart and checkout CTAs stay visible on small screens
- [ ] Ensure forms are easy to use on mobile keyboards
- [ ] Ensure upload prescription flow works on mobile camera/file upload
- [ ] Test on:
  - [ ] small Android
  - [ ] iPhone size
  - [ ] tablet
  - [ ] desktop
- [ ] Fix overflow, clipping, and touch target issues
- [ ] Optimize images and JS for slower mobile devices

## 10. Security Hardening

Use OWASP ASVS as the baseline for verification.

- [ ] Apply Django production deployment checklist
- [ ] Enforce HTTPS everywhere
- [ ] Set secure cookies
- [ ] Set CSRF protection correctly
- [ ] Set strict CORS policy
- [ ] Add content security policy
- [ ] Add security headers:
  - [ ] `X-Frame-Options`
  - [ ] `X-Content-Type-Options`
  - [ ] `Referrer-Policy`
  - [ ] `Permissions-Policy`
- [ ] Add request rate limiting
- [ ] Add API abuse protection
- [ ] Add admin and pharmacist audit logs
- [ ] Encrypt sensitive data where required
- [ ] Store secrets in proper secret management, not source code
- [ ] Restrict database access by network and least privilege
- [ ] Add dependency vulnerability scanning
- [ ] Add container image scanning
- [ ] Add WAF / bot protection in production
- [ ] Add incident response and credential rotation procedure

## 11. Observability and Operations

- [ ] Add structured backend logging
- [ ] Add frontend error tracking
- [ ] Add backend error tracking
- [ ] Add metrics and dashboards
- [ ] Add uptime checks
- [ ] Add alerting for:
  - [ ] API down
  - [ ] DB unavailable
  - [ ] Redis unavailable
  - [ ] queue backlog
  - [ ] failed payments
  - [ ] failed notifications
  - [ ] rising error rate
- [ ] Add audit dashboards for ops teams
- [ ] Add health/readiness checks for all core services

## 12. Performance and Scale

- [ ] Add caching strategy for hot reads
- [ ] Add CDN strategy for static/media assets
- [ ] Add DB query profiling and optimization
- [ ] Add pagination on all large listing endpoints
- [ ] Add async jobs for slow or retryable workflows
- [ ] Add load tests for:
  - [ ] search
  - [ ] product detail
  - [ ] cart
  - [ ] checkout
  - [ ] prescription upload
- [ ] Define when to introduce:
  - [ ] `OpenSearch`
  - [ ] `Kafka`
  - [ ] service extraction

## 13. Testing

- [ ] Add backend unit tests
- [ ] Add backend API integration tests
- [ ] Add permission tests
- [ ] Add Celery task tests
- [ ] Add frontend component tests
- [ ] Add frontend integration tests
- [ ] Add Playwright e2e tests for:
  - [ ] login
  - [ ] search
  - [ ] product detail
  - [ ] upload prescription
  - [ ] cart
  - [ ] checkout
  - [ ] admin flows
  - [ ] pharmacist flows
- [ ] Add responsive visual QA checklist

## 14. Compliance and Pharmacy-Specific Controls

- [ ] Show legal pharmacy/license details where required
- [ ] Restrict sale of prescription-only medicines correctly
- [ ] Add prescription review traceability
- [ ] Add medicine substitution approval logic
- [ ] Add region-specific availability restrictions
- [ ] Add invoice retention policy
- [ ] Add pharmacist action history
- [ ] Add privacy-consent tracking where needed

## 15. CI/CD and Release Safety

- [ ] Add CI pipeline
- [ ] Add lint checks
- [ ] Add type checks
- [ ] Add backend test stage
- [ ] Add frontend test stage
- [ ] Add build stage
- [ ] Add migration safety checks
- [ ] Add security scan stage
- [ ] Add staging deployment
- [ ] Add rollback procedure
- [ ] Add release checklist

## 16. Immediate Next Priority

Build these next in order:

1. `users`
2. `catalog`
3. `prescriptions`
4. connect frontend to live APIs
5. replace mock cart and order data
6. add mobile QA pass
7. add security baseline hardening
