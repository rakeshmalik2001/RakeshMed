# RakeshMed Production Blueprint

## 1. Product Scope

RakeshMed is being positioned as a real pharmacy platform, not a frontend-only demo. The product must support:

- Customer storefront for OTC and prescription medicines
- Prescription upload, pharmacist review, and substitution workflow
- Search by medicine, salt, category, and brand
- Address and pincode-based delivery eligibility
- Cart, checkout, payment, refunds, and invoices
- Customer accounts, orders, and reorder/refill journeys
- Admin operations for catalog, inventory, orders, promotions, and compliance
- Pharmacist operations for review queues, approvals, rejections, and escalation
- Event-driven notifications and audit visibility

## 2. Final Recommended Stack

### Frontend

- `Next.js` with App Router
- `TypeScript`
- Shared design system inside `apps/web`
- API integration against `Django REST Framework`

### Core Backend

- `Python 3.12+`
- `Django`
- `Django REST Framework`
- `PostgreSQL`
- `Redis`
- `Celery`

### Scale and Search

- `OpenSearch` for high-scale catalog/search
- `Kafka` when event throughput justifies service decoupling
- `S3-compatible storage` for prescriptions, invoices, and product assets

### Infra

- `Docker`
- `Kubernetes`
- `Nginx` or API gateway
- `Prometheus + Grafana + Sentry`

## 3. Architecture Strategy

### Phase 1: Modular Monolith

This is the correct starting point for a medicine platform:

- `apps/web` contains storefront, account, admin, and pharmacist UI surfaces
- `apps/api` contains Django + DRF backend modules
- `PostgreSQL` is the transactional source of truth
- `Redis` handles cache, OTP/session support, and Celery broker/result backend
- `Celery` handles background jobs

### Phase 2: Service Extraction

Split only the hottest or most operationally sensitive domains:

- search/autocomplete
- notifications
- webhook ingestion
- analytics/event pipeline
- recommendation service

The core medicine, prescription, and order logic should stay in the main Django platform until real scale demands extraction.

## 4. Current Repository Direction

The repository is now aligned to this structure:

```text
RakeshMed/
  apps/
    web/
      src/
        app/
        components/
        lib/
        styles/
    api/
      config/
        settings/
      platform_apps/
        health/
      manage.py
      requirements.txt
  docker-compose.yml
  .env.example
  README.md
```

## 5. Target Domain Modules

Build the backend as domain-driven Django apps:

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

Recommended later modules:

11. `promotions`
12. `cms`
13. `analytics`
14. `support`
15. `warehouse`

## 6. Frontend Areas

The web app should continue to serve four major experience areas:

1. Public marketing pages
2. Customer storefront and account
3. Admin back office
4. Pharmacist operations

These areas can stay in the same Next.js app initially, with route groups and shared layout primitives.

## 7. Backend Responsibilities

### Django + DRF should own:

- auth and role enforcement
- customer identity
- medicine catalog
- salt and substitute logic
- prescription workflow
- cart and checkout validation
- order placement and lifecycle
- refund orchestration
- delivery/serviceability rules
- audit trails

### Celery should own:

- OTP delivery jobs
- email/SMS/WhatsApp notifications
- webhook retry jobs
- invoice generation
- stock sync and low-stock alerts
- prescription review SLA timers

## 8. Database Design Direction

### Core tables

- `users`
- `roles`
- `addresses`
- `family_members`
- `products`
- `product_variants`
- `categories`
- `brands`
- `salts`
- `product_salts`
- `product_substitutes`
- `inventory`
- `warehouses`
- `pincodes`
- `prescriptions`
- `prescription_reviews`
- `carts`
- `cart_items`
- `orders`
- `order_items`
- `payments`
- `refunds`
- `shipments`
- `notifications`
- `audit_logs`

### Key medicine/product fields

- `name`
- `slug`
- `sku`
- `brand_id`
- `category_id`
- `composition`
- `dosage_form`
- `strength`
- `pack_size`
- `mrp`
- `sale_price`
- `requires_prescription`
- `manufacturer`
- `warnings`
- `side_effects`
- `storage_instructions`

### Prescription fields

- `prescription_number`
- `user_id`
- `patient_name`
- `doctor_name`
- `uploaded_file_url`
- `status`
- `reviewed_by`
- `review_notes`
- `reviewed_at`
- `expires_at`

### Order fields

- `order_number`
- `user_id`
- `status`
- `payment_status`
- `fulfillment_status`
- `subtotal`
- `discount_total`
- `delivery_fee`
- `tax_total`
- `grand_total`
- `prescription_id`

## 9. API Structure

Use versioned REST APIs under `/api/v1`.

### Public and customer APIs

- `POST /api/v1/auth/send-otp/`
- `POST /api/v1/auth/verify-otp/`
- `GET /api/v1/catalog/products/`
- `GET /api/v1/catalog/products/{slug}/`
- `GET /api/v1/catalog/categories/`
- `GET /api/v1/search/`
- `POST /api/v1/cart/items/`
- `PATCH /api/v1/cart/items/{id}/`
- `POST /api/v1/checkout/validate/`
- `POST /api/v1/orders/`
- `GET /api/v1/orders/`
- `GET /api/v1/orders/{id}/`
- `POST /api/v1/prescriptions/upload/`

### Admin APIs

- `GET /api/v1/admin/dashboard/`
- `POST /api/v1/admin/products/`
- `PATCH /api/v1/admin/products/{id}/`
- `PATCH /api/v1/admin/inventory/{id}/`
- `GET /api/v1/admin/orders/`
- `PATCH /api/v1/admin/orders/{id}/status/`
- `GET /api/v1/admin/prescriptions/`
- `PATCH /api/v1/admin/prescriptions/{id}/review/`

### Platform APIs already scaffolded

- `GET /api/v1/health/live/`
- `GET /api/v1/health/ready/`

## 10. Roles and Permissions

Primary roles:

- `customer`
- `admin`
- `catalog_manager`
- `pharmacist`
- `warehouse_operator`
- `support_agent`
- `finance`

Critical permission groups:

- product create/update/publish
- stock update
- order refund/cancel
- prescription approve/reject
- coupon and CMS publish
- audit log access

## 11. Search and Catalog Intelligence

Search should evolve in layers:

### Initial layer

- PostgreSQL full-text search
- `pg_trgm` typo tolerance
- category and brand filters

### Scale layer

- `OpenSearch`
- synonym dictionaries
- salt-based substitute discovery
- autocomplete
- out-of-stock fallback suggestions

## 12. Compliance and Security

This is non-negotiable for a pharmacy platform:

- private prescription storage with signed URLs
- encryption at rest for sensitive documents
- audit every pharmacist/admin action
- rate limiting for auth and checkout flows
- CSRF/XSS/SQLi protection
- secure cookie/session handling
- retention and deletion policy for prescriptions/invoices
- region-specific medicine restrictions
- pharmacist/license display where legally required

## 13. Non-Functional Targets

- core page load under `2.5s`
- common read API `p95 < 300ms`
- `99.9%` uptime target for customer flows
- horizontal scalability at web and worker layers
- structured logs, tracing, alerting, backups, and restore drills

## 14. Testing Strategy

### Frontend

- unit tests for components and hooks
- integration tests for cart and checkout flows
- e2e tests for login, search, prescription upload, and checkout

### Backend

- unit tests for domain services
- API integration tests
- role/permission tests
- worker task tests
- load tests for search and checkout

## 15. Recommended Build Order

1. finalize auth and role model
2. build `catalog`
3. build `cart`
4. build `prescriptions`
5. build `orders`
6. build `inventory`
7. wire notifications and background jobs
8. add OpenSearch and scale hardening

## 16. Immediate Next Step

The repository already has:

- Next.js app in `apps/web`
- Django API scaffold in `apps/api`
- Postgres/Redis/API compose file
- health endpoints

The next real implementation step is:

1. create Django apps for `users`, `catalog`, and `prescriptions`
2. connect `apps/web` to real `/api/v1/...` endpoints
3. replace mock catalog/cart/prescription data with database-backed APIs
