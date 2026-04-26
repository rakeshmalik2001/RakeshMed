# RakeshMed Page List and Wireframe Structure

## 1. Interface Areas

The platform is split into four frontend experience areas inside `apps/web`:

1. Public marketing website
2. Customer storefront and account
3. Admin back office
4. Pharmacist operations panel

Each page should map cleanly to backend modules in `apps/api`.

## 2. Global Layout System

### Public Website Layout

- top utility bar
- main header with search, categories, login, cart, upload prescription CTA
- content body
- footer with trust/compliance links

### Customer Storefront Layout

- sticky header
- category navigation
- breadcrumb on category and product pages
- mini-cart or quick cart access
- toast notifications
- mobile bottom navigation

### Admin and Pharmacist Layout

- left sidebar
- topbar with alerts and search
- main data table/card area
- action toolbar
- detail drawer or review panel

## 3. Storefront Page List

### Marketing and Discovery

1. Home
2. About
3. Contact
4. Serviceability
5. Offers
6. Download App
7. FAQ
8. Terms
9. Privacy
10. Prescription Policy
11. Health Guide / Blog

### Catalog and Shopping

12. Categories Landing
13. Category Listing
14. Subcategory Listing
15. Search Results
16. Product Detail
17. Substitute/Alternative View
18. Vitamins Landing
19. Personal Care Landing
20. Devices Landing
21. OTC Landing
22. Prescription Medicines Landing

### Prescription Flow

23. Upload Prescription
24. Prescription Submitted
25. Prescription Pending
26. Prescription Approved
27. Prescription Rejected
28. Prescription Detail

### Cart and Checkout

29. Cart
30. Checkout Address
31. Checkout Payment
32. Checkout Review
33. Checkout Success

### Authentication

34. Login
35. Verify OTP

### Customer Account

36. Account Dashboard
37. Orders List
38. Order Detail
39. Saved Prescriptions
40. Saved Addresses
41. Family Members
42. Notifications
43. Support

## 4. Admin Page List

1. Admin Dashboard
2. Products
3. Add/Edit Product
4. Categories
5. Brands
6. Salts/Compositions
7. Inventory
8. Warehouses
9. Orders
10. Prescription Queue
11. Customers
12. Coupons and Promotions
13. CMS Pages
14. Notification Templates
15. Reports
16. Roles and Permissions
17. Audit Logs

## 5. Pharmacist Page List

1. Pharmacist Dashboard
2. Prescription Review Queue
3. Prescription Detail Review
4. Clarification Requests
5. Approved Prescriptions
6. Rejected Prescriptions
7. Substitute Requests
8. Audit Trail
9. Escalation Queue

## 6. Page-to-Backend Module Mapping

### Customer-facing module mapping

- login / verify OTP -> `users`
- categories / product detail / search -> `catalog`
- upload prescription -> `prescriptions`
- cart -> `cart`
- checkout / order success -> `orders`, `payments`, `delivery`
- account orders -> `orders`

### Operations module mapping

- admin products / categories -> `catalog`
- admin inventory -> `inventory`
- admin orders -> `orders`
- pharmacist queue -> `prescriptions`
- audit and tracking screens -> `audit`

## 7. Home Page Wireframe

```text
+----------------------------------------------------------------------------------+
| TOP BAR: support | offers | upload prescription | pincode                        |
+----------------------------------------------------------------------------------+
| HEADER: logo | search | category nav | account | cart                            |
+----------------------------------------------------------------------------------+
| HERO SEARCH + TRUST MESSAGE                                                      |
| [Search medicines] [Upload Prescription] [Check Serviceability]                  |
+----------------------------------------------------------------------------------+
| QUICK ACTIONS                                                                    |
| upload prescription | buy again | offers | devices | chronic care                |
+----------------------------------------------------------------------------------+
| SHOP BY CATEGORY                                                                 |
+----------------------------------------------------------------------------------+
| BESTSELLERS / TRENDING                                                           |
+----------------------------------------------------------------------------------+
| PRESCRIPTION CTA                                                                 |
+----------------------------------------------------------------------------------+
| CONTENT / FAQ / TRUST                                                            |
+----------------------------------------------------------------------------------+
| FOOTER                                                                           |
+----------------------------------------------------------------------------------+
```

## 8. Category Listing Wireframe

```text
+----------------------------------------------------------------------------------+
| HEADER                                                                            |
+----------------------------------------------------------------------------------+
| BREADCRUMB                                                                        |
+----------------------------------------------------------------------------------+
| HERO: category title | short description | banner                                 |
+----------------------------------------------------------------------------------+
| FILTER + SORT BAR                                                                 |
+----------------------------------------------------------------------------------+
| SIDEBAR FILTERS     | PRODUCT GRID                                                |
| brand               | [Product card] [Product card] [Product card]                |
| price               | [Product card] [Product card] [Product card]                |
| prescription        | [Product card] [Product card] [Product card]                |
| form                | pagination                                                  |
+----------------------------------------------------------------------------------+
| SEO CONTENT / FAQ                                                                 |
+----------------------------------------------------------------------------------+
```

### Product card essentials

- product image
- medicine name
- composition/salt
- pack size
- MRP and sale price
- prescription badge
- stock state
- add to cart

## 9. Product Detail Wireframe

```text
+----------------------------------------------------------------------------------+
| HEADER                                                                            |
+----------------------------------------------------------------------------------+
| BREADCRUMB                                                                        |
+----------------------------------------------------------------------------------+
| GALLERY            | PRODUCT INFO                                                 |
| thumbs             | name                                                         |
| image              | brand / manufacturer                                         |
|                    | composition                                                  |
|                    | prescription badge                                           |
|                    | pack size / form / strength                                  |
|                    | price / savings                                              |
|                    | pincode check                                                |
|                    | qty | add to cart | upload prescription                      |
+----------------------------------------------------------------------------------+
| INFORMATION TABS                                                                  |
| overview | uses | dosage | warnings | side effects | storage                      |
+----------------------------------------------------------------------------------+
| SUBSTITUTES                                                                        |
+----------------------------------------------------------------------------------+
| RELATED PRODUCTS                                                                   |
+----------------------------------------------------------------------------------+
```

## 10. Upload Prescription Wireframe

```text
+----------------------------------------------------------------------------------+
| HEADER                                                                            |
+----------------------------------------------------------------------------------+
| TITLE: Upload Prescription                                                        |
+----------------------------------------------------------------------------------+
| LEFT: rules and help   | RIGHT: upload form                                       |
| accepted formats       | drag/drop zone                                            |
| how review works       | patient name                                              |
| privacy note           | doctor name                                               |
| pharmacist SLA         | notes                                                     |
|                        | [Upload Prescription]                                     |
+----------------------------------------------------------------------------------+
| HOW IT WORKS                                                                     |
+----------------------------------------------------------------------------------+
| FAQ / COMPLIANCE                                                                 |
+----------------------------------------------------------------------------------+
```

## 11. Cart and Checkout Wireframe

### Cart

```text
+----------------------------------------------------------------------------------+
| CART ITEMS                                        | ORDER SUMMARY                 |
| medicine card                                     | subtotal                      |
| qty controls                                      | discount                      |
| prescription state                                | delivery                      |
| remove                                            | total                         |
|                                                   | [Proceed to Checkout]         |
+----------------------------------------------------------------------------------+
| PRESCRIPTION ALERT / RECOMMENDATIONS                                             |
+----------------------------------------------------------------------------------+
```

### Checkout steps

1. address
2. payment
3. review
4. success

Keep the checkout flow backed by real API validation rather than frontend-only mock state.

## 12. Account Dashboard Wireframe

```text
+----------------------------------------------------------------------------------+
| ACCOUNT HEADER                                                                    |
+----------------------------------------------------------------------------------+
| SIDEBAR                | MAIN                                                     |
| dashboard              | recent orders                                            |
| orders                 | saved prescriptions                                      |
| addresses              | refill reminders                                         |
| family members         | support quick links                                      |
| notifications          |                                                           |
+----------------------------------------------------------------------------------+
```

## 13. Admin Dashboard Wireframe

```text
+----------------------------------------------------------------------------------+
| SIDEBAR                | TOP BAR                                                  |
+----------------------------------------------------------------------------------+
| KPI CARDS                                                                         |
| orders | revenue | pending prescriptions | low stock                              |
+----------------------------------------------------------------------------------+
| CHARTS                                                                            |
| sales trend | prescription SLA | top categories                                   |
+----------------------------------------------------------------------------------+
| OPERATIONS TABLES                                                                 |
| latest orders | urgent prescriptions | stock alerts                               |
+----------------------------------------------------------------------------------+
```

## 14. Prescription Review Queue Wireframe

```text
+----------------------------------------------------------------------------------+
| QUEUE FILTERS: pending | clarification | approved | rejected                      |
+----------------------------------------------------------------------------------+
| LEFT: queue list         | RIGHT: review detail                                   |
| patient                  | prescription image/PDF                                 |
| upload time              | extracted medicines                                    |
| order link               | patient and doctor details                             |
| SLA badge                | notes                                                   |
|                          | [Approve] [Reject] [Clarify] [Substitute]              |
+----------------------------------------------------------------------------------+
```

## 15. Reusable Component Inventory

Core components should include:

- header
- footer
- search bar
- product card
- medicine badge
- prescription-required badge
- price block
- quantity selector
- pincode checker
- address card
- order summary card
- status chip
- timeline
- upload dropzone
- filters sidebar
- data table
- drawer/modal
- notification toast

## 16. MVP Page Cut

Build these first against real backend APIs:

1. Home
2. Category Listing
3. Search Results
4. Product Detail
5. Upload Prescription
6. Cart
7. Checkout Address
8. Checkout Payment
9. Checkout Review
10. Checkout Success
11. Login / Verify OTP
12. Orders List
13. Order Detail
14. Admin Dashboard
15. Products
16. Inventory
17. Prescription Review Queue

## 17. Next Deliverables

After this page structure, the next useful assets are:

1. database schema by module
2. API contract list by page
3. role/permission matrix
4. frontend state integration plan
5. Django app model and serializer plan
