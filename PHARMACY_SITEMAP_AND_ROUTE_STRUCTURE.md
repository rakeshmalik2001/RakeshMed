# RakeshMed Sitemap and Route Structure

## 1. Route Strategy

Use route groups by experience area in the Next.js app:

```text
apps/web/src/app/
  (marketing)/
  (shop)/
  (auth)/
  account/
  admin/
  pharmacist/
```

Use versioned backend routes in Django:

```text
/api/v1/
```

## 2. Public and Storefront Sitemap

```text
/
|-- /about
|-- /contact
|-- /offers
|-- /serviceability
|-- /download-app
|-- /faq
|-- /terms
|-- /privacy
|-- /prescription-policy
|-- /blog
|   |-- /blog/[slug]
|-- /health-guide
|   |-- /health-guide/[slug]
|-- /categories
|   |-- /categories/[categorySlug]
|   |   |-- /categories/[categorySlug]/[subcategorySlug]
|   |   |   |-- /categories/[categorySlug]/[subcategorySlug]/[itemSlug]
|-- /search
|-- /products/[productSlug]
|-- /medicine/[productSlug]
|-- /cart
```

## 3. Authentication Sitemap

```text
/login
/verify-otp
```

## 4. Prescription Sitemap

```text
/upload-prescription
|-- /upload-prescription/submitted
|-- /upload-prescription/pending
|-- /upload-prescription/approved
|-- /upload-prescription/rejected
```

## 5. Checkout Sitemap

```text
/checkout/address
/checkout/payment
/checkout/review
/checkout/success
```

## 6. Customer Account Sitemap

```text
/account
|-- /account/orders
|   |-- /account/orders/[orderId]
```

Recommended later additions:

```text
/account/profile
/account/addresses
/account/prescriptions
/account/family-members
/account/notifications
/account/support
```

## 7. Admin Sitemap

```text
/admin
|-- /admin/dashboard
|-- /admin/products
|-- /admin/inventory
```

Recommended later additions:

```text
/admin/orders
/admin/prescriptions
/admin/categories
/admin/brands
/admin/salts
/admin/warehouses
/admin/customers
/admin/coupons
/admin/cms
/admin/reports
/admin/audit-logs
```

## 8. Pharmacist Sitemap

```text
/pharmacist
|-- /pharmacist/prescriptions
|   |-- /pharmacist/prescriptions/[prescriptionId]
```

Recommended later additions:

```text
/pharmacist/clarifications
/pharmacist/approved
/pharmacist/rejected
/pharmacist/substitute-requests
/pharmacist/audit-trail
/pharmacist/escalations
```

## 9. Backend API Namespace Plan

Django API routes should be organized by module:

```text
/api/v1/
  auth/
  users/
  catalog/
  search/
  prescriptions/
  cart/
  checkout/
  orders/
  payments/
  inventory/
  delivery/
  notifications/
  admin/
  pharmacist/
  health/
```

## 10. Current Backend Routes

Already scaffolded:

```text
/api/v1/health/live/
/api/v1/health/ready/
```

Recommended next API route groups to implement:

```text
/api/v1/auth/send-otp/
/api/v1/auth/verify-otp/
/api/v1/catalog/categories/
/api/v1/catalog/products/
/api/v1/catalog/products/{slug}/
/api/v1/search/
/api/v1/prescriptions/upload/
/api/v1/cart/items/
/api/v1/orders/
```

## 11. Recommended App Router Structure

```text
apps/web/src/app/
  (marketing)/
    page.tsx
    about/page.tsx
    contact/page.tsx
    offers/page.tsx
    serviceability/page.tsx
    download-app/page.tsx
    faq/page.tsx
    terms/page.tsx
    privacy/page.tsx
    prescription-policy/page.tsx
    blog/[[...slug]]/page.tsx
    health-guide/[[...slug]]/page.tsx

  (shop)/
    categories/page.tsx
    categories/[categorySlug]/page.tsx
    categories/[categorySlug]/[subcategorySlug]/page.tsx
    categories/[categorySlug]/[subcategorySlug]/[itemSlug]/page.tsx
    search/page.tsx
    products/[productSlug]/page.tsx
    medicine/[productSlug]/page.tsx
    cart/page.tsx
    checkout/address/page.tsx
    checkout/payment/page.tsx
    checkout/review/page.tsx
    checkout/success/page.tsx
    upload-prescription/page.tsx
    upload-prescription/submitted/page.tsx
    upload-prescription/pending/page.tsx
    upload-prescription/approved/page.tsx
    upload-prescription/rejected/page.tsx

  (auth)/
    login/page.tsx
    verify-otp/page.tsx

  account/
    page.tsx
    orders/page.tsx
    orders/[orderId]/page.tsx

  admin/
    page.tsx
    dashboard/page.tsx
    products/page.tsx
    inventory/page.tsx

  pharmacist/
    page.tsx
    prescriptions/page.tsx
    prescriptions/[prescriptionId]/page.tsx
```

## 12. Backend Django App Structure

```text
apps/api/
  config/
    settings/
  platform_apps/
    health/
    users/
    catalog/
    prescriptions/
    cart/
    orders/
    inventory/
    notifications/
    audit/
```

The current repository only scaffolds `health/`. The remaining apps should be added next in this same structure.

## 13. Route Guards

Protect routes by role:

- public: marketing, category, product, search
- authenticated customer: cart persistence, checkout, account
- admin only: `/admin/**`
- pharmacist only: `/pharmacist/**`

Additional protections:

- block order placement if prescription-required items are unresolved
- enforce role checks in Django permissions, not just frontend guards
- log pharmacist and admin actions in audit trails

## 14. Dynamic Route Parameters

Use these route params:

- `categorySlug`
- `subcategorySlug`
- `itemSlug`
- `productSlug`
- `orderId`
- `prescriptionId`

## 15. MVP Route Cut

Frontend MVP:

- `/`
- `/categories/[categorySlug]`
- `/search`
- `/products/[productSlug]`
- `/upload-prescription`
- `/cart`
- `/checkout/address`
- `/checkout/payment`
- `/checkout/review`
- `/checkout/success`
- `/login`
- `/verify-otp`
- `/account/orders`
- `/account/orders/[orderId]`
- `/admin/dashboard`
- `/admin/products`
- `/admin/inventory`
- `/pharmacist/prescriptions`
- `/pharmacist/prescriptions/[prescriptionId]`

Backend MVP:

- `/api/v1/auth/send-otp/`
- `/api/v1/auth/verify-otp/`
- `/api/v1/catalog/categories/`
- `/api/v1/catalog/products/`
- `/api/v1/catalog/products/{slug}/`
- `/api/v1/search/`
- `/api/v1/prescriptions/upload/`
- `/api/v1/cart/items/`
- `/api/v1/orders/`
- `/api/v1/health/live/`
- `/api/v1/health/ready/`

## 16. What This Enables Next

This route structure now supports:

1. real frontend-to-backend API mapping
2. Django app ownership by domain
3. role-based route enforcement
4. database schema planning by module
5. progressive scale-out without reorganizing the whole repo later
