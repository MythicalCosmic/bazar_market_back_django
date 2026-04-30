# Bazar Market - Admin API Guide

**Base URL:** `https://api.bazarmarket.org/admin-api`

All endpoints are prefixed with `/admin-api/`. For example, to list users:
```
GET https://api.bazarmarket.org/admin-api/users
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Users (Staff)](#2-users-staff)
3. [Customers](#3-customers)
4. [Addresses](#4-addresses)
5. [Categories](#5-categories)
6. [Products](#6-products)
7. [Orders](#7-orders)
8. [Banners](#8-banners)
9. [Coupons](#9-coupons)
10. [Discounts](#10-discounts)
11. [Delivery Zones](#11-delivery-zones)
12. [Reviews](#12-reviews)
13. [Payments](#13-payments)
14. [Notifications](#14-notifications)
15. [Roles & Permissions](#15-roles--permissions)
16. [Settings](#16-settings)
17. [Favorites](#17-favorites)
18. [Stats & Analytics](#18-stats--analytics)
19. [Error Handling](#19-error-handling)
20. [Rate Limiting](#20-rate-limiting)
21. [Pagination](#21-pagination)

---

## General Info

### Headers

All requests must include:
```
Content-Type: application/json
```

Protected endpoints (everything except login) require:
```
Authorization: Bearer <session_key>
```

### Authentication & Permissions

Every protected endpoint checks two things:
1. **Session** — valid, non-expired session token
2. **Permission** — the user's role (+ any per-user overrides) must include the required permission

Roles: `admin`, `manager`, `courier`. Admin has all permissions by default.

### Response Format

Every response follows this structure:

**Success:**
```json
{
  "success": true,
  "message": "Optional message",
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "message": "Error description"
}
```

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created (new resource) |
| 400 | Bad request / invalid input |
| 401 | Not authenticated (missing or invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 405 | Method not allowed |
| 422 | Validation error |
| 429 | Rate limited |
| 500 | Server error |

---

## 1. Authentication

### 1.1 Login

Authenticates a staff user and returns a session key.

```
POST /admin-api/auth-login
```

**Rate limit:** 5 requests per minute (per IP)

**Auth required:** No

**Body:**
```json
{
  "username": "admin",
  "password": "test1234",
  "device": "Chrome Desktop"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Staff username |
| password | string | Yes | Account password |
| device | string | No | Device name for session tracking |

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "session_key": "a1b2c3d4e5f6...",
    "user": {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "username": "admin",
      "first_name": "Admin",
      "last_name": "Bazarov",
      "role": "admin"
    },
    "expires_at": "2026-05-02T12:00:00+05:00"
  }
}
```

**Important:** Save the `session_key` — use it in the `Authorization: Bearer <session_key>` header for all subsequent requests.

**Errors:**
- `"Username and password are required"` — missing fields
- `"User not found"` — username does not exist
- `"Invalid credentials"` — wrong password

---

### 1.2 Get Profile (Me)

```
GET /admin-api/auth-me
```

**Rate limit:** 30 requests per minute (per IP)

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "message": "Profile retrieval successful",
  "data": {
    "id": 1,
    "username": "admin",
    "full_name": "Admin Bazarov",
    "role": "admin"
  }
}
```

---

### 1.3 Logout

Invalidates the current session.

```
POST /admin-api/auth-logout
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "message": "Logout successful",
  "data": { "message": "Logged out" }
}
```

---

### 1.4 Logout All Devices

Invalidates all active sessions for the current user.

```
POST /admin-api/auth-logout-all
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "message": "Logout successful for all devices",
  "data": { "message": "Logged out" }
}
```

---

## 2. Users (Staff)

Manage admin, manager, and courier accounts. Requires `view_users` / `manage_users` permission.

### 2.1 List Users

```
GET /admin-api/users
```

**Permission:** `view_users`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by name, username, or phone |
| role | string | Filter: `admin`, `manager`, `courier` |
| is_active | string | `true` or `false` |
| is_deleted | string | `true` to show soft-deleted users |
| order_by | string | `created_at`, `first_name`, `last_name`, `role` (prefix `-` for desc) |
| page | int | Page number (default: 1) |
| per_page | int | Items per page, 1-100 (default: 20) |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "uuid": "550e8400-...",
        "username": "admin",
        "first_name": "Admin",
        "last_name": "Bazarov",
        "phone": "+998901234567",
        "role": "admin",
        "language": "uz",
        "telegram_id": null,
        "is_active": true,
        "last_seen_at": "2026-04-29T12:00:00+05:00",
        "created_at": "2026-04-01T10:00:00+05:00"
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 6,
    "total_pages": 1
  }
}
```

---

### 2.2 Get User

```
GET /admin-api/user/{user_id}
```

**Permission:** `view_users`

**Response (200):** same structure as a single item from list.

**Errors:**
- 404 `"User not found"`

---

### 2.3 Create User

```
POST /admin-api/user/create
```

**Permission:** `manage_users`

**Body:**
```json
{
  "username": "newmanager",
  "first_name": "Sardor",
  "last_name": "Karimov",
  "role": "manager",
  "password": "securepass123",
  "phone": "+998901111111",
  "language": "uz",
  "telegram_id": 123456
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Unique username |
| first_name | string | Yes | First name |
| last_name | string | Yes | Last name |
| role | string | Yes | `admin`, `manager`, or `courier` |
| password | string | Yes | Will be hashed |
| phone | string | No | Unique phone number |
| language | string | No | `uz` or `ru` (default: `uz`) |
| telegram_id | integer | No | Telegram user ID |

**Response (201):**
```json
{
  "success": true,
  "message": "User created",
  "data": {
    "id": 7,
    "username": "newmanager",
    "first_name": "Sardor",
    "last_name": "Karimov"
  }
}
```

**Errors:**
- `"Role must be one of: admin, manager, courier"` — invalid role
- `"Username already exists"` — duplicate username
- `"Phone already exists"` — duplicate phone

---

### 2.4 Update User

```
PATCH /admin-api/user/{user_id}/update
```

**Permission:** `manage_users`

**Body:** (all fields optional)
```json
{
  "first_name": "Updated Name",
  "password": "newpassword123"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "User updated",
  "data": {
    "id": 7,
    "username": "newmanager",
    "first_name": "Updated Name",
    "last_name": "Karimov"
  }
}
```

---

### 2.5 Delete User (Soft Delete)

```
DELETE /admin-api/user/{user_id}/delete
```

**Permission:** `manage_users`

Soft-deletes the user and invalidates all their sessions.

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "User deleted successfully" }
}
```

---

### 2.6 Restore User

```
POST /admin-api/user/{user_id}/restore
```

**Permission:** `manage_users`

Restores a soft-deleted user.

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "User restored successfully" }
}
```

**Errors:**
- `"User not found or not deleted"` — user doesn't exist or isn't deleted

---

## 3. Customers

Manage client (customer) accounts. Requires `view_users` / `manage_users` permission.

### 3.1 List Customers

```
GET /admin-api/customers
```

**Permission:** `view_users`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by name, phone, or telegram ID |
| is_active | string | `true` or `false` |
| order_by | string | `created_at`, `first_name`, `last_name` (prefix `-` for desc) |
| page | int | Page number (default: 1) |
| per_page | int | Items per page (default: 20) |

**Response (200):** Paginated list of customer objects.

---

### 3.2 Get Customer (Detail)

Returns a customer with all related data: addresses, orders, favorites, and reviews.

```
GET /admin-api/customer/{customer_id}
```

**Permission:** `view_users`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 7,
    "uuid": "...",
    "first_name": "Aziza",
    "last_name": "Umarova",
    "phone": "+998911111101",
    "telegram_id": 200001,
    "language": "uz",
    "is_active": true,
    "last_seen_at": "2026-04-29T12:00:00+05:00",
    "created_at": "2026-04-01T10:00:00+05:00",
    "addresses": [
      {
        "id": 1,
        "label": "Uy",
        "address_text": "Chilanzar 9, dom 45",
        "is_default": true
      }
    ],
    "orders": [
      {
        "id": 1,
        "order_number": "ORD-20260429-0001",
        "status": "delivered",
        "total": "150000.00",
        "created_at": "2026-04-28T10:00:00+05:00"
      }
    ],
    "favorites": [
      {
        "id": 1,
        "product_id": 5,
        "product_name": "Olma"
      }
    ],
    "reviews": [
      {
        "id": 1,
        "order_number": "ORD-20260429-0001",
        "rating": 5,
        "comment": "Juda yaxshi!"
      }
    ]
  }
}
```

---

### 3.3 Update Customer

```
PATCH /admin-api/customer/{customer_id}/update
```

**Permission:** `manage_users`

**Body:** (all optional)
```json
{
  "first_name": "Updated",
  "phone": "+998911111199"
}
```

---

### 3.4 Deactivate Customer

```
POST /admin-api/customer/{customer_id}/deactivate
```

**Permission:** `manage_users`

---

### 3.5 Activate Customer

```
POST /admin-api/customer/{customer_id}/activate
```

**Permission:** `manage_users`

---

## 4. Addresses

View customer addresses. Read-only from admin panel. Requires `view_users` permission.

### 4.1 List All Addresses

```
GET /admin-api/addresses
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| user_id | int | Filter by user |
| is_active | string | `true` or `false` |
| order_by | string | `-created_at` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 4.2 Get User's Addresses

```
GET /admin-api/addresses/user/{user_id}
```

Returns all addresses for a specific user (non-paginated array).

---

### 4.3 Get Single Address

```
GET /admin-api/address/{address_id}
```

---

## 5. Categories

Manage product categories with parent-child hierarchy. Requires `view_categories` / `manage_categories` permission.

### 5.1 List Categories

```
GET /admin-api/categories
```

**Permission:** `view_categories`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by name |
| is_active | string | `true` or `false` |
| parent_id | int | Filter by parent category |
| is_deleted | string | `true` for soft-deleted |
| order_by | string | `sort_order` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 5.2 Category Tree

Returns the full category tree (parents with nested children).

```
GET /admin-api/categories/tree
```

**Permission:** `view_categories`

---

### 5.3 Get Category

```
GET /admin-api/category/{category_id}
```

**Permission:** `view_categories`

---

### 5.4 Create Category

```
POST /admin-api/category/create
```

**Permission:** `manage_categories`

**Body:**
```json
{
  "name_uz": "Mevalar",
  "name_ru": "Фрукты",
  "image": "https://example.com/fruits.jpg",
  "parent_id": null,
  "sort_order": 0,
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name_uz | string | Yes | Name in Uzbek |
| name_ru | string | No | Name in Russian |
| image | string | No | Image URL |
| parent_id | int/null | No | Parent category ID for subcategories |
| sort_order | int | No | Display order (default: 0) |
| is_active | bool | No | Active status (default: true) |

---

### 5.5 Update Category

```
PATCH /admin-api/category/{category_id}/update
```

**Permission:** `manage_categories`

**Body:** any subset of create fields.

---

### 5.6 Delete Category (Soft)

```
DELETE /admin-api/category/{category_id}/delete
```

**Permission:** `manage_categories`

---

### 5.7 Restore Category

```
POST /admin-api/category/{category_id}/restore
```

**Permission:** `manage_categories`

---

### 5.8 Reorder Categories

```
POST /admin-api/categories/reorder
```

**Permission:** `manage_categories`

**Body:**
```json
{
  "ids": [3, 1, 2, 5, 4]
}
```

Sets `sort_order` based on array position.

---

### 5.9 Activate / Deactivate Category

```
POST /admin-api/category/{category_id}/activate
POST /admin-api/category/{category_id}/deactivate
```

**Permission:** `manage_categories`

---

## 6. Products

Full product CRUD with images, stock, and discount management. Requires `view_products` / `manage_products` permission.

### 6.1 List Products

```
GET /admin-api/products
```

**Permission:** `view_products`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by name |
| category_id | int | Filter by category |
| is_active | string | `true` or `false` |
| in_stock | string | `true` or `false` |
| is_featured | string | `true` or `false` |
| unit | string | `kg`, `piece`, `liter`, `pack`, `bundle` |
| min_price | decimal | Minimum price |
| max_price | decimal | Maximum price |
| has_discount | string | `true` or `false` |
| stock_status | string | Stock status filter |
| has_sku | string | `true` or `false` |
| has_barcode | string | `true` or `false` |
| order_by | string | `-created_at` (default), `price`, `name_uz`, etc. |
| page | int | Page number |
| per_page | int | Items per page |

**Response item:**
```json
{
  "id": 1,
  "uuid": "...",
  "category_id": 5,
  "category_name": "Olma",
  "name_uz": "Olma",
  "name_ru": "",
  "sku": "APL-001",
  "barcode": "4901234567890",
  "unit": "kg",
  "price": "15000.00",
  "cost_price": "10000.00",
  "margin": 33.3,
  "in_stock": true,
  "stock_qty": "250.000",
  "low_stock_threshold": "10.000",
  "is_low_stock": false,
  "sort_order": 0,
  "is_active": true,
  "is_featured": false,
  "created_at": "2026-04-01T10:00:00+05:00",
  "primary_image": "https://..."
}
```

---

### 6.2 Get Product (Detail)

```
GET /admin-api/product/{product_id}
```

**Permission:** `view_products`

Returns the full product with `description_uz`, `description_ru`, `step`, `min_qty`, `max_qty`, `images[]`, and `discounts[]`.

---

### 6.3 Create Product

```
POST /admin-api/product/create
```

**Permission:** `manage_products`

**Body:**
```json
{
  "category_id": 5,
  "name_uz": "Yangi olma",
  "name_ru": "Новые яблоки",
  "unit": "kg",
  "price": "18000",
  "cost_price": "12000",
  "sku": "APL-002",
  "barcode": "4901234567891",
  "description_uz": "Toza olma",
  "step": "0.5",
  "min_qty": "0.5",
  "max_qty": "10",
  "in_stock": true,
  "stock_qty": "100",
  "low_stock_threshold": "10",
  "sort_order": 0,
  "is_active": true,
  "is_featured": false,
  "images": [
    { "image": "https://example.com/apple.jpg", "is_primary": true }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| category_id | int | Yes | Category ID |
| name_uz | string | Yes | Name in Uzbek |
| unit | string | Yes | `kg`, `piece`, `liter`, `pack`, `bundle` |
| price | decimal | Yes | Price per unit in som |
| name_ru | string | No | Name in Russian |
| description_uz | string | No | Description in Uzbek |
| description_ru | string | No | Description in Russian |
| sku | string | No | Stock keeping unit code |
| barcode | string | No | Product barcode |
| cost_price | decimal | No | Wholesale/cost price for margin calc |
| step | decimal | No | Purchase step, e.g. 0.5 = buy in 0.5kg increments (default: 1) |
| min_qty | decimal | No | Minimum quantity per order (default: 1) |
| max_qty | decimal | No | Maximum quantity per order (null = unlimited) |
| in_stock | bool | No | In stock (default: true) |
| stock_qty | decimal | No | Stock quantity (null = unlimited) |
| low_stock_threshold | decimal | No | Alert when stock drops below this |
| sort_order | int | No | Display order (default: 0) |
| is_active | bool | No | Active (default: true) |
| is_featured | bool | No | Featured on homepage (default: false) |
| images | array | No | Array of `{ image, is_primary, sort_order }` |

---

### 6.4 Update Product

```
PATCH /admin-api/product/{product_id}/update
```

**Permission:** `manage_products`

**Body:** any subset of create fields.

---

### 6.5 Delete / Restore Product

```
DELETE /admin-api/product/{product_id}/delete
POST   /admin-api/product/{product_id}/restore
```

**Permission:** `manage_products`

---

### 6.6 Reorder Products

```
POST /admin-api/products/reorder
```

**Permission:** `manage_products`

**Body:** `{ "ids": [3, 1, 2] }`

---

### 6.7 Activate / Deactivate / Feature / Unfeature

```
POST /admin-api/product/{product_id}/activate
POST /admin-api/product/{product_id}/deactivate
POST /admin-api/product/{product_id}/feature
POST /admin-api/product/{product_id}/unfeature
```

**Permission:** `manage_products`

---

### 6.8 Update Stock

```
POST /admin-api/product/{product_id}/stock
```

**Permission:** `manage_products`

**Body:**
```json
{
  "stock_qty": "100",
  "in_stock": true
}
```

---

### 6.9 Manage Images

**Add images:**
```
POST /admin-api/product/{product_id}/images
```
**Body:** `{ "images": [{ "image": "https://...", "is_primary": false }] }`

**Remove image:**
```
DELETE /admin-api/product/{product_id}/image/{image_id}
```

**Reorder images:**
```
POST /admin-api/product/{product_id}/images/reorder
```
**Body:** `{ "ids": [2, 1, 3] }`

**Set primary image:**
```
POST /admin-api/product/{product_id}/image/{image_id}/primary
```

**Permission:** `manage_products` for all

---

### 6.10 Assign / Remove Discounts

```
POST /admin-api/product/{product_id}/discounts/assign
POST /admin-api/product/{product_id}/discounts/remove
```

**Permission:** `manage_products`

**Body:** `{ "discount_ids": [1, 2] }`

---

## 7. Orders

View and manage customer orders. Permissions: `view_orders`, `manage_orders`, `assign_orders`, `manage_payments`.

### 7.1 List Orders

```
GET /admin-api/orders
```

**Permission:** `view_orders`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by order number, customer name, phone |
| status | string | `pending`, `confirmed`, `preparing`, `delivering`, `delivered`, `completed`, `cancelled` |
| payment_status | string | `unpaid`, `pending`, `paid`, `refunded` |
| payment_method | string | `cash`, `click`, `payme` |
| user_id | int | Filter by customer |
| courier_id | int | Filter by assigned courier |
| has_courier | string | `true` or `false` |
| date_from | ISO date | Start date filter |
| date_to | ISO date | End date filter |
| min_total | decimal | Minimum order total |
| max_total | decimal | Maximum order total |
| order_by | string | `-created_at` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 7.2 Get Order (Detail)

```
GET /admin-api/order/{order_id}
```

**Permission:** `view_orders`

Returns the full order with items, address, courier info, and status log.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "uuid": "...",
    "order_number": "ORD-20260429-0001",
    "status": "confirmed",
    "total": "150000.00",
    "subtotal": "145000.00",
    "delivery_fee": "10000.00",
    "discount": "5000.00",
    "payment_method": "cash",
    "payment_status": "unpaid",
    "delivery_address_text": "Chilanzar 9, dom 45",
    "user_note": "Iltimos tezroq",
    "admin_note": "",
    "created_at": "2026-04-28T10:00:00+05:00",
    "confirmed_at": "2026-04-28T10:05:00+05:00",
    "user": {
      "id": 7,
      "first_name": "Aziza",
      "last_name": "Umarova",
      "phone": "+998911111101",
      "role": "client"
    },
    "courier": null,
    "address": {
      "id": 1,
      "label": "Uy",
      "address_text": "Chilanzar 9, dom 45",
      "latitude": "41.2856000",
      "longitude": "69.2042000"
    },
    "items": [
      {
        "id": 1,
        "product_id": 5,
        "product_name": "Olma",
        "unit": "kg",
        "unit_price": "15000.00",
        "quantity": "2.000",
        "total": "30000.00"
      }
    ],
    "status_log": [
      {
        "from_status": "",
        "to_status": "pending",
        "changed_by": null,
        "note": "",
        "created_at": "2026-04-28T10:00:00+05:00"
      }
    ]
  }
}
```

---

### 7.3 Update Order Status

```
POST /admin-api/order/{order_id}/status
```

**Permission:** `manage_orders`

**Body:**
```json
{
  "status": "confirmed",
  "note": "Order verified by manager"
}
```

**Valid transitions:**
```
pending → confirmed → preparing → delivering → delivered → completed
```

---

### 7.4 Assign / Unassign Courier

```
POST /admin-api/order/{order_id}/assign-courier
```
**Body:** `{ "courier_id": 4 }`

```
POST /admin-api/order/{order_id}/unassign-courier
```
**Body:** empty

**Permission:** `assign_orders`

---

### 7.5 Update Payment Status

```
POST /admin-api/order/{order_id}/payment-status
```

**Permission:** `manage_payments`

**Body:** `{ "payment_status": "paid" }`

---

### 7.6 Add Admin Note

```
POST /admin-api/order/{order_id}/note
```

**Permission:** `manage_orders`

**Body:** `{ "note": "Customer called about delivery time" }`

---

### 7.7 Cancel Order

```
POST /admin-api/order/{order_id}/cancel
```

**Permission:** `manage_orders`

**Body:** `{ "reason": "Customer requested cancellation" }`

---

### 7.8 Bulk Update Status

```
POST /admin-api/orders/bulk-status
```

**Permission:** `manage_orders`

**Body:**
```json
{
  "order_ids": [1, 2, 3],
  "status": "confirmed",
  "note": "Batch confirmed"
}
```

---

### 7.9 Accept & Print / Print Order

```
POST /admin-api/order/{order_id}/accept-print
```
Confirms the order and enqueues a receipt print job.

```
POST /admin-api/order/{order_id}/print
```
Enqueues a print job for any order (does not change status).

**Permission:** `manage_orders`

---

### 7.10 Minimum Order Settings

```
GET  /admin-api/orders/min-order
POST /admin-api/orders/min-order/set
```

**Body (set):** `{ "amount": 30000 }`

**Permission:** `view_analytics` (get) / `manage_settings` (set)

---

## 8. Banners

Manage promotional banners. Requires `manage_banners` permission.

### 8.1 List Banners

```
GET /admin-api/banners
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| is_active | string | `true` or `false` |
| scheduled | string | Filter by schedule status |
| order_by | string | `sort_order` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 8.2 Get / Create / Update / Delete Banner

```
GET    /admin-api/banner/{banner_id}
POST   /admin-api/banner/create
PATCH  /admin-api/banner/{banner_id}/update
DELETE /admin-api/banner/{banner_id}/delete
```

**Create body:**
```json
{
  "image": "https://example.com/banner.jpg",
  "title": "Yangi mahsulotlar!",
  "link_type": "category",
  "link_value": "5",
  "sort_order": 0,
  "starts_at": "2026-04-29T00:00:00+05:00",
  "expires_at": "2026-05-29T00:00:00+05:00",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| image | string | Yes | Banner image URL |
| title | string | No | Banner title |
| link_type | string | No | `category`, `product`, `url`, `none` (default: `none`) |
| link_value | string | No | Category ID, product ID, or URL |
| sort_order | int | No | Display order |
| starts_at | ISO date | No | Schedule start |
| expires_at | ISO date | No | Schedule end |
| is_active | bool | No | Active (default: true) |

---

### 8.3 Reorder / Activate / Deactivate

```
POST /admin-api/banners/reorder           Body: { "ids": [3, 1, 2] }
POST /admin-api/banner/{banner_id}/activate
POST /admin-api/banner/{banner_id}/deactivate
```

---

## 9. Coupons

Manage discount coupon codes. Requires `manage_coupons` permission.

### 9.1 List Coupons

```
GET /admin-api/coupons
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by code |
| is_active | string | `true` or `false` |
| type | string | `percent` or `fixed` |
| valid_only | string | `true` for currently valid coupons only |
| order_by | string | `-created_at` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 9.2 Get / Create / Update / Delete Coupon

```
GET    /admin-api/coupon/{coupon_id}
POST   /admin-api/coupon/create
PATCH  /admin-api/coupon/{coupon_id}/update
DELETE /admin-api/coupon/{coupon_id}/delete
```

**Create body:**
```json
{
  "code": "YANGI2026",
  "type": "percent",
  "value": 10,
  "min_order": 50000,
  "max_discount": 20000,
  "usage_limit": 100,
  "per_user_limit": 1,
  "starts_at": "2026-04-01T00:00:00+05:00",
  "expires_at": "2026-07-01T00:00:00+05:00",
  "is_active": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | Yes | Unique coupon code |
| type | string | Yes | `percent` or `fixed` |
| value | decimal | Yes | 10 for 10% or 10000 for 10k som |
| min_order | decimal | No | Minimum order total to apply |
| max_discount | decimal | No | Cap for percent type |
| usage_limit | int | No | Total uses allowed (null = unlimited) |
| per_user_limit | int | No | Uses per user (default: 1) |
| starts_at | ISO date | No | Valid from |
| expires_at | ISO date | No | Valid until |
| is_active | bool | No | Active (default: true) |

---

### 9.3 Activate / Deactivate

```
POST /admin-api/coupon/{coupon_id}/activate
POST /admin-api/coupon/{coupon_id}/deactivate
```

---

## 10. Discounts

Manage product/category discounts. Requires `manage_discounts` permission.

### 10.1 List Discounts

```
GET /admin-api/discounts
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by name |
| is_active | string | `true` or `false` |
| type | string | `percent` or `fixed` |
| current_only | string | `true` for currently active discounts |
| order_by | string | `-created_at` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 10.2 Get / Create / Update / Delete / Restore

```
GET    /admin-api/discount/{discount_id}
POST   /admin-api/discount/create
PATCH  /admin-api/discount/{discount_id}/update
DELETE /admin-api/discount/{discount_id}/delete
POST   /admin-api/discount/{discount_id}/restore
```

**Create body:**
```json
{
  "name_uz": "Yozgi chegirma",
  "name_ru": "Летняя скидка",
  "type": "percent",
  "value": 15,
  "max_discount": 25000,
  "starts_at": "2026-06-01T00:00:00+05:00",
  "expires_at": "2026-08-31T23:59:59+05:00",
  "is_active": true,
  "product_ids": [1, 2, 3],
  "category_ids": [5]
}
```

---

### 10.3 Activate / Deactivate

```
POST /admin-api/discount/{discount_id}/activate
POST /admin-api/discount/{discount_id}/deactivate
```

---

### 10.4 Manage Discount Targets

**Products:**
```
POST /admin-api/discount/{discount_id}/products/set     Body: { "product_ids": [1, 2] }
POST /admin-api/discount/{discount_id}/products/add     Body: { "product_ids": [3] }
POST /admin-api/discount/{discount_id}/products/remove  Body: { "product_ids": [2] }
```

**Categories:**
```
POST /admin-api/discount/{discount_id}/categories/set     Body: { "category_ids": [1] }
POST /admin-api/discount/{discount_id}/categories/add     Body: { "category_ids": [2] }
POST /admin-api/discount/{discount_id}/categories/remove  Body: { "category_ids": [1] }
```

- `set` replaces all current targets
- `add` appends to existing targets
- `remove` removes from existing targets

---

## 11. Delivery Zones

Manage delivery zones with GeoJSON polygons. Requires `view_delivery_zones` / `manage_delivery_zones` permission.

### 11.1 List Zones

```
GET /admin-api/zones
```

**Permission:** `view_delivery_zones`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| is_active | string | `true` or `false` |
| order_by | string | `sort_order` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 11.2 Get / Create / Update / Delete Zone

```
GET    /admin-api/zone/{zone_id}
POST   /admin-api/zone/create
PATCH  /admin-api/zone/{zone_id}/update
DELETE /admin-api/zone/{zone_id}/delete
```

**Permission:** `view_delivery_zones` (get) / `manage_delivery_zones` (create/update/delete)

**Create body:**
```json
{
  "name": "Chilanzar",
  "polygon": {
    "type": "Polygon",
    "coordinates": [[[69.18, 41.28], [69.22, 41.28], [69.22, 41.31], [69.18, 41.31], [69.18, 41.28]]]
  },
  "delivery_fee": "10000",
  "min_order": "50000",
  "estimated_minutes": 30,
  "is_active": true,
  "sort_order": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Zone name (e.g. "Chilanzar") |
| polygon | GeoJSON | Yes | Polygon coordinates |
| delivery_fee | decimal | Yes | Delivery fee in som |
| min_order | decimal | No | Minimum order for this zone (default: 0) |
| estimated_minutes | int | No | Estimated delivery time |
| is_active | bool | No | Active (default: true) |
| sort_order | int | No | Display order |

---

### 11.3 Reorder / Activate / Deactivate

```
POST /admin-api/zones/reorder                  Body: { "ids": [2, 1, 3] }
POST /admin-api/zone/{zone_id}/activate
POST /admin-api/zone/{zone_id}/deactivate
```

---

## 12. Reviews

Moderate customer reviews. Requires `view_reviews` / `manage_reviews` permission.

### 12.1 List Reviews

```
GET /admin-api/reviews
```

**Permission:** `view_reviews`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by comment, customer name, phone, order number |
| rating | int | Filter by rating (1-5) |
| moderation_status | string | `pending`, `approved`, `rejected` |
| user_id | int | Filter by customer |
| order_by | string | `-created_at` (default), `rating`, `moderation_status` |
| page | int | Page number |
| per_page | int | Items per page |

**Response item:**
```json
{
  "id": 1,
  "rating": 5,
  "comment": "Juda yaxshi xizmat!",
  "admin_reply": "",
  "moderation_status": "pending",
  "created_at": "2026-04-28T14:00:00+05:00",
  "user": {
    "id": 7,
    "first_name": "Aziza",
    "last_name": "Umarova",
    "phone": "+998911111101"
  },
  "order": {
    "id": 1,
    "order_number": "ORD-20260429-0001"
  }
}
```

---

### 12.2 Get Review

```
GET /admin-api/review/{review_id}
```

**Permission:** `view_reviews`

Also includes `moderated_by` and `moderated_at` fields.

---

### 12.3 Approve / Reject Review

```
POST /admin-api/review/{review_id}/approve
POST /admin-api/review/{review_id}/reject
```

**Permission:** `manage_reviews`

**Body:** empty

---

### 12.4 Reply to Review

```
POST /admin-api/review/{review_id}/reply
```

**Permission:** `manage_reviews`

**Body:**
```json
{
  "reply": "Rahmat! Xizmatimizdan mamnun bo'lganingiz uchun tashakkur."
}
```

---

### 12.5 Delete Review

```
DELETE /admin-api/review/{review_id}/delete
```

**Permission:** `manage_reviews`

---

### 12.6 Bulk Approve / Reject

```
POST /admin-api/reviews/bulk-approve
POST /admin-api/reviews/bulk-reject
```

**Permission:** `manage_reviews`

**Body:**
```json
{
  "review_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "success": true,
  "data": { "approved": 3, "skipped": 0 }
}
```

---

## 13. Payments

View and manage payment records. Requires `view_payments` / `manage_payments` permission.

### 13.1 List Payments

```
GET /admin-api/payments
```

**Permission:** `view_payments`

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by order number or customer phone |
| status | string | `pending`, `processing`, `completed`, `failed`, `refunded` |
| method | string | `click`, `payme`, `cash` |
| order_id | int | Filter by order |
| date_from | ISO date | Start date |
| date_to | ISO date | End date |
| min_amount | decimal | Minimum amount |
| max_amount | decimal | Maximum amount |
| order_by | string | `-created_at` (default), `amount`, `status`, `method`, `paid_at` |
| page | int | Page number |
| per_page | int | Items per page |

**Response item:**
```json
{
  "id": 1,
  "uuid": "...",
  "method": "click",
  "amount": "150000.00",
  "status": "completed",
  "paid_at": "2026-04-28T10:30:00+05:00",
  "created_at": "2026-04-28T10:00:00+05:00",
  "order": {
    "id": 1,
    "order_number": "ORD-20260429-0001",
    "user": {
      "id": 7,
      "first_name": "Aziza",
      "phone": "+998911111101"
    }
  }
}
```

---

### 13.2 Get Payment

```
GET /admin-api/payment/{payment_id}
```

**Permission:** `view_payments`

---

### 13.3 Payments by Order

```
GET /admin-api/payments/order/{order_id}
```

**Permission:** `view_payments`

Returns array of all payments for a given order.

---

### 13.4 Update Payment Status

```
POST /admin-api/payment/{payment_id}/status
```

**Permission:** `manage_payments`

**Body:** `{ "status": "completed" }`

**Valid transitions:**
```
pending → processing, completed, failed
processing → completed, failed
completed → refunded
```

When status is set to `completed`, the order's payment_status is automatically updated to `paid`.

---

### 13.5 Refund Payment

```
POST /admin-api/payment/{payment_id}/refund
```

**Permission:** `manage_payments`

**Body:** `{ "reason": "Customer request" }`

Only completed payments can be refunded. Also updates the order's payment_status to `refunded`.

---

## 14. Notifications

Send and manage notifications to users. Requires `manage_notifications` permission.

### 14.1 List Notifications

```
GET /admin-api/notifications
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| q | string | Search by title, body, customer name, phone |
| type | string | `order_status`, `promo`, `system` |
| channel | string | `telegram`, `sms`, `push` |
| is_read | string | `true` or `false` |
| user_id | int | Filter by user |
| order_by | string | `-sent_at` (default), `type`, `channel` |
| page | int | Page number |
| per_page | int | Items per page |

---

### 14.2 Get Notification

```
GET /admin-api/notification/{notification_id}
```

---

### 14.3 Send to User

```
POST /admin-api/notification/user/{user_id}/send
```

**Body:**
```json
{
  "title": "Maxsus taklif!",
  "body": "Bugun barcha mevalar 20% chegirmada!",
  "type": "promo",
  "channel": "telegram",
  "payload": { "category_id": 1 }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | Yes | Notification title |
| body | string | Yes | Notification body |
| type | string | No | `order_status`, `promo`, `system` (default: `promo`) |
| channel | string | No | `telegram`, `sms`, `push` (default: `telegram`) |
| payload | object | No | Extra data for deep linking |

---

### 14.4 Send Bulk

```
POST /admin-api/notifications/send
```

**Body:**
```json
{
  "title": "Chegirma!",
  "body": "Barcha mijozlar uchun 15% chegirma!",
  "type": "promo",
  "channel": "telegram",
  "user_ids": [7, 8, 9],
  "role": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| title | string | Yes | Title |
| body | string | Yes | Body |
| type | string | No | Notification type (default: `promo`) |
| channel | string | No | Delivery channel (default: `telegram`) |
| user_ids | array | No | Send to specific users (if provided, `role` is ignored) |
| role | string | No | Send to all users with this role (e.g. `client`) |

If neither `user_ids` nor `role` is provided, sends to **all active users**.

---

### 14.5 Delete Notification / Delete User's Notifications

```
DELETE /admin-api/notification/{notification_id}/delete
DELETE /admin-api/notification/user/{user_id}/delete
```

---

## 15. Roles & Permissions

Manage the RBAC system. Requires `manage_roles` permission. Only admins have this by default.

### 15.1 List All Permissions

```
GET /admin-api/permissions
```

**Query:** `?group=orders` (optional, filter by group)

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "id": 1, "codename": "manage_users", "name": "Manage users", "group": "users" },
    { "id": 2, "codename": "view_orders", "name": "View orders", "group": "orders" }
  ]
}
```

---

### 15.2 List Permission Groups

```
GET /admin-api/permissions/groups
```

**Response:** `["catalog", "delivery", "orders", "reviews", "system", "users"]`

---

### 15.3 Sync Permissions

Creates any permissions defined in code that don't exist in the database yet.

```
POST /admin-api/permissions/sync
```

**Response:** `{ "synced": 3, "total": 23 }`

---

### 15.4 Get Role Permissions

```
GET /admin-api/role/{role}/permissions
```

**Path params:** `role` = `admin`, `manager`, `courier`, `client`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "role": "manager",
    "permissions": [
      { "id": 1, "codename": "manage_categories", "name": "Manage categories", "group": "catalog" }
    ]
  }
}
```

---

### 15.5 Set Role Permissions

Replaces all permissions for a role.

```
POST /admin-api/role/{role}/permissions/set
```

**Body:**
```json
{
  "permissions": ["view_orders", "manage_orders", "assign_orders"]
}
```

**Note:** Cannot modify `admin` role permissions.

---

### 15.6 Reset Role to Defaults

```
POST /admin-api/role/{role}/permissions/reset
```

Resets to the default permissions defined in code.

---

### 15.7 User-Level Permission Overrides

Per-user overrides that add or remove permissions beyond their role.

**View overrides:**
```
GET /admin-api/user/{user_id}/permissions
```

**Grant (add permission):**
```
POST /admin-api/user/{user_id}/permissions/grant
Body: { "permission": "manage_orders" }
```

**Deny (revoke permission):**
```
POST /admin-api/user/{user_id}/permissions/deny
Body: { "permission": "manage_orders" }
```

**Remove override (revert to role default):**
```
DELETE /admin-api/user/{user_id}/permissions/remove
Body: { "permission": "manage_orders" }
```

**Clear all overrides:**
```
DELETE /admin-api/user/{user_id}/permissions/clear
```

---

## 16. Settings

Key-value application settings. Requires `manage_settings` permission.

### 16.1 List All Settings

```
GET /admin-api/settings
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "key": "working_hours_start",
      "value": "08:00",
      "type": "string",
      "description": "Store opening time",
      "updated_at": "2026-04-01T10:00:00+05:00"
    },
    {
      "key": "min_order_total",
      "value": 30000,
      "type": "int",
      "description": "Minimum order total in som",
      "updated_at": "2026-04-01T10:00:00+05:00"
    }
  ]
}
```

---

### 16.2 Get Setting

```
GET /admin-api/setting/{key}
```

Example: `GET /admin-api/setting/working_hours_start`

---

### 16.3 Set Setting

Creates or updates a setting.

```
POST /admin-api/settings/set
```

**Body:**
```json
{
  "key": "delivery_fee",
  "value": "9000",
  "type": "int",
  "description": "Flat delivery fee in som"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| key | string | Yes | Setting key |
| value | any | Yes | Setting value |
| type | string | No | `string`, `int`, `bool`, `json` (default: `string`) |
| description | string | No | Human-readable description |

---

### 16.4 Delete Setting

```
DELETE /admin-api/setting/{key}/delete
```

---

## 17. Favorites

Read-only view of customer favorites for analytics. Requires `view_analytics` permission.

### 17.1 List Favorites

```
GET /admin-api/favorites
```

**Query parameters:**

| Param | Type | Description |
|-------|------|-------------|
| user_id | int | Filter by customer |
| product_id | int | Filter by product |
| order_by | string | `-created_at` (default) |
| page | int | Page number |
| per_page | int | Items per page |

---

### 17.2 Most Favorited Products

```
GET /admin-api/favorites/most
```

**Query:** `?limit=20` (default: 20)

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "product_id": 5,
      "name": "Olma",
      "price": "15000.00",
      "favorite_count": 42
    }
  ]
}
```

---

## 18. Stats & Analytics

All stats endpoints require `view_analytics` permission and support optional `date_from` / `date_to` query params (ISO date format).

| Endpoint | Description |
|----------|-------------|
| `GET /admin-api/stats/overview` | Overall dashboard stats |
| `GET /admin-api/stats/staff` | Staff activity stats |
| `GET /admin-api/stats/customers` | Customer stats (supports `?lat=...&lng=...` for geo) |
| `GET /admin-api/stats/categories` | Category performance |
| `GET /admin-api/stats/products` | Product stats (supports `?category_id=...`) |
| `GET /admin-api/stats/orders` | Order stats |
| `GET /admin-api/stats/banners` | Banner performance |
| `GET /admin-api/stats/coupons` | Coupon usage stats |
| `GET /admin-api/stats/discounts` | Discount stats |
| `GET /admin-api/stats/zones` | Delivery zone stats |
| `GET /admin-api/stats/reviews` | Review moderation stats |
| `GET /admin-api/stats/payments` | Revenue & payment stats |
| `GET /admin-api/stats/notifications` | Notification delivery stats |
| `GET /admin-api/stats/favorites` | Favorite analytics |

**Example — Review Stats Response:**
```json
{
  "success": true,
  "data": {
    "total": 150,
    "average_rating": 4.3,
    "by_rating": { "1": 5, "2": 8, "3": 20, "4": 45, "5": 72 },
    "by_moderation_status": { "pending": 12, "approved": 130, "rejected": 8 },
    "pending": 12,
    "approved": 130,
    "rejected": 8,
    "with_comment": 120,
    "with_reply": 45
  }
}
```

**Example — Payment Stats Response:**
```json
{
  "success": true,
  "data": {
    "total": 500,
    "by_status": { "pending": 10, "completed": 450, "failed": 30, "refunded": 10 },
    "by_method": { "cash": 200, "click": 180, "payme": 120 },
    "revenue": "75000000.00",
    "avg_payment": "166666.67",
    "refunded_amount": "1500000.00",
    "refund_count": 10,
    "pending_amount": "2000000.00",
    "completed_count": 450,
    "failed_count": 30
  }
}
```

---

## 19. Error Handling

All errors follow the same format:

```json
{
  "success": false,
  "message": "Error description"
}
```

| Code | When |
|------|------|
| 401 | Missing `Authorization` header, invalid session, or expired session |
| 403 | Valid session but user lacks the required permission |
| 404 | Resource not found (user, order, product, etc.) |
| 422 | Validation error (missing required fields, invalid values, business rule violations) |
| 429 | Rate limited (login and /me endpoints) |

**Common error messages:**
- `"Authorization header required"` — missing Bearer token
- `"Invalid or expired session"` — session doesn't exist or expired
- `"You do not have permission to perform this action"` — insufficient permissions
- `"Invalid JSON body"` — malformed request body
- `"Too many requests. Please try again later."` — rate limited

---

## 20. Rate Limiting

Rate limits are per-IP, backed by Redis.

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /admin-api/auth-login` | 5 requests | 60 seconds |
| `GET /admin-api/auth-me` | 30 requests | 60 seconds |

When rate limited, the response includes:
```
HTTP 429
Retry-After: <seconds>
```

All other endpoints are not rate limited at the application level.

---

## 21. Pagination

All list endpoints use consistent pagination:

**Request:** `?page=1&per_page=20`

- `page` — page number, starts at 1 (default: 1)
- `per_page` — items per page, 1-100 (default: 20)

**Response:**
```json
{
  "items": [ ... ],
  "page": 1,
  "per_page": 20,
  "total": 45,
  "total_pages": 3
}
```

---

## Quick Reference Table

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/admin-api/auth-login` | POST | — | Login |
| `/admin-api/auth-me` | GET | — | Get profile |
| `/admin-api/auth-logout` | POST | — | Logout |
| `/admin-api/auth-logout-all` | POST | — | Logout all devices |
| `/admin-api/users` | GET | view_users | List staff users |
| `/admin-api/user/:id` | GET | view_users | Get user |
| `/admin-api/user/create` | POST | manage_users | Create user |
| `/admin-api/user/:id/update` | PATCH | manage_users | Update user |
| `/admin-api/user/:id/delete` | DELETE | manage_users | Soft delete user |
| `/admin-api/user/:id/restore` | POST | manage_users | Restore user |
| `/admin-api/customers` | GET | view_users | List customers |
| `/admin-api/customer/:id` | GET | view_users | Customer detail (with relations) |
| `/admin-api/customer/:id/update` | PATCH | manage_users | Update customer |
| `/admin-api/customer/:id/deactivate` | POST | manage_users | Deactivate customer |
| `/admin-api/customer/:id/activate` | POST | manage_users | Activate customer |
| `/admin-api/addresses` | GET | view_users | List addresses |
| `/admin-api/addresses/user/:id` | GET | view_users | User's addresses |
| `/admin-api/address/:id` | GET | view_users | Get address |
| `/admin-api/categories` | GET | view_categories | List categories |
| `/admin-api/categories/tree` | GET | view_categories | Category tree |
| `/admin-api/categories/reorder` | POST | manage_categories | Reorder |
| `/admin-api/category/:id` | GET | view_categories | Get category |
| `/admin-api/category/create` | POST | manage_categories | Create |
| `/admin-api/category/:id/update` | PATCH | manage_categories | Update |
| `/admin-api/category/:id/delete` | DELETE | manage_categories | Soft delete |
| `/admin-api/category/:id/restore` | POST | manage_categories | Restore |
| `/admin-api/category/:id/activate` | POST | manage_categories | Activate |
| `/admin-api/category/:id/deactivate` | POST | manage_categories | Deactivate |
| `/admin-api/products` | GET | view_products | List products |
| `/admin-api/products/reorder` | POST | manage_products | Reorder |
| `/admin-api/product/:id` | GET | view_products | Product detail |
| `/admin-api/product/create` | POST | manage_products | Create |
| `/admin-api/product/:id/update` | PATCH | manage_products | Update |
| `/admin-api/product/:id/delete` | DELETE | manage_products | Soft delete |
| `/admin-api/product/:id/restore` | POST | manage_products | Restore |
| `/admin-api/product/:id/activate` | POST | manage_products | Activate |
| `/admin-api/product/:id/deactivate` | POST | manage_products | Deactivate |
| `/admin-api/product/:id/feature` | POST | manage_products | Feature |
| `/admin-api/product/:id/unfeature` | POST | manage_products | Unfeature |
| `/admin-api/product/:id/stock` | POST | manage_products | Update stock |
| `/admin-api/product/:id/images` | POST | manage_products | Add images |
| `/admin-api/product/:id/images/reorder` | POST | manage_products | Reorder images |
| `/admin-api/product/:id/image/:img_id` | DELETE | manage_products | Remove image |
| `/admin-api/product/:id/image/:img_id/primary` | POST | manage_products | Set primary |
| `/admin-api/product/:id/discounts/assign` | POST | manage_products | Assign discounts |
| `/admin-api/product/:id/discounts/remove` | POST | manage_products | Remove discounts |
| `/admin-api/orders` | GET | view_orders | List orders |
| `/admin-api/orders/bulk-status` | POST | manage_orders | Bulk status update |
| `/admin-api/orders/min-order` | GET | view_analytics | Get min order |
| `/admin-api/orders/min-order/set` | POST | manage_settings | Set min order |
| `/admin-api/order/:id` | GET | view_orders | Order detail |
| `/admin-api/order/:id/status` | POST | manage_orders | Update status |
| `/admin-api/order/:id/assign-courier` | POST | assign_orders | Assign courier |
| `/admin-api/order/:id/unassign-courier` | POST | assign_orders | Unassign courier |
| `/admin-api/order/:id/payment-status` | POST | manage_payments | Payment status |
| `/admin-api/order/:id/note` | POST | manage_orders | Add admin note |
| `/admin-api/order/:id/cancel` | POST | manage_orders | Cancel order |
| `/admin-api/order/:id/accept-print` | POST | manage_orders | Accept & print |
| `/admin-api/order/:id/print` | POST | manage_orders | Print receipt |
| `/admin-api/banners` | GET | manage_banners | List banners |
| `/admin-api/banners/reorder` | POST | manage_banners | Reorder |
| `/admin-api/banner/:id` | GET | manage_banners | Get banner |
| `/admin-api/banner/create` | POST | manage_banners | Create |
| `/admin-api/banner/:id/update` | PATCH | manage_banners | Update |
| `/admin-api/banner/:id/delete` | DELETE | manage_banners | Delete |
| `/admin-api/banner/:id/activate` | POST | manage_banners | Activate |
| `/admin-api/banner/:id/deactivate` | POST | manage_banners | Deactivate |
| `/admin-api/coupons` | GET | manage_coupons | List coupons |
| `/admin-api/coupon/:id` | GET | manage_coupons | Get coupon |
| `/admin-api/coupon/create` | POST | manage_coupons | Create |
| `/admin-api/coupon/:id/update` | PATCH | manage_coupons | Update |
| `/admin-api/coupon/:id/delete` | DELETE | manage_coupons | Delete |
| `/admin-api/coupon/:id/activate` | POST | manage_coupons | Activate |
| `/admin-api/coupon/:id/deactivate` | POST | manage_coupons | Deactivate |
| `/admin-api/discounts` | GET | manage_discounts | List discounts |
| `/admin-api/discount/:id` | GET | manage_discounts | Get discount |
| `/admin-api/discount/create` | POST | manage_discounts | Create |
| `/admin-api/discount/:id/update` | PATCH | manage_discounts | Update |
| `/admin-api/discount/:id/delete` | DELETE | manage_discounts | Soft delete |
| `/admin-api/discount/:id/restore` | POST | manage_discounts | Restore |
| `/admin-api/discount/:id/activate` | POST | manage_discounts | Activate |
| `/admin-api/discount/:id/deactivate` | POST | manage_discounts | Deactivate |
| `/admin-api/discount/:id/products/set` | POST | manage_discounts | Set products |
| `/admin-api/discount/:id/products/add` | POST | manage_discounts | Add products |
| `/admin-api/discount/:id/products/remove` | POST | manage_discounts | Remove products |
| `/admin-api/discount/:id/categories/set` | POST | manage_discounts | Set categories |
| `/admin-api/discount/:id/categories/add` | POST | manage_discounts | Add categories |
| `/admin-api/discount/:id/categories/remove` | POST | manage_discounts | Remove categories |
| `/admin-api/zones` | GET | view_delivery_zones | List zones |
| `/admin-api/zones/reorder` | POST | manage_delivery_zones | Reorder |
| `/admin-api/zone/:id` | GET | view_delivery_zones | Get zone |
| `/admin-api/zone/create` | POST | manage_delivery_zones | Create |
| `/admin-api/zone/:id/update` | PATCH | manage_delivery_zones | Update |
| `/admin-api/zone/:id/delete` | DELETE | manage_delivery_zones | Delete |
| `/admin-api/zone/:id/activate` | POST | manage_delivery_zones | Activate |
| `/admin-api/zone/:id/deactivate` | POST | manage_delivery_zones | Deactivate |
| `/admin-api/reviews` | GET | view_reviews | List reviews |
| `/admin-api/reviews/bulk-approve` | POST | manage_reviews | Bulk approve |
| `/admin-api/reviews/bulk-reject` | POST | manage_reviews | Bulk reject |
| `/admin-api/review/:id` | GET | view_reviews | Get review |
| `/admin-api/review/:id/approve` | POST | manage_reviews | Approve |
| `/admin-api/review/:id/reject` | POST | manage_reviews | Reject |
| `/admin-api/review/:id/reply` | POST | manage_reviews | Reply |
| `/admin-api/review/:id/delete` | DELETE | manage_reviews | Delete |
| `/admin-api/payments` | GET | view_payments | List payments |
| `/admin-api/payment/:id` | GET | view_payments | Get payment |
| `/admin-api/payment/:id/status` | POST | manage_payments | Update status |
| `/admin-api/payment/:id/refund` | POST | manage_payments | Refund |
| `/admin-api/payments/order/:id` | GET | view_payments | Payments by order |
| `/admin-api/notifications` | GET | manage_notifications | List |
| `/admin-api/notifications/send` | POST | manage_notifications | Bulk send |
| `/admin-api/notification/:id` | GET | manage_notifications | Get |
| `/admin-api/notification/:id/delete` | DELETE | manage_notifications | Delete |
| `/admin-api/notification/user/:id/send` | POST | manage_notifications | Send to user |
| `/admin-api/notification/user/:id/delete` | DELETE | manage_notifications | Delete user's |
| `/admin-api/permissions` | GET | manage_roles | List permissions |
| `/admin-api/permissions/groups` | GET | manage_roles | Permission groups |
| `/admin-api/permissions/sync` | POST | manage_roles | Sync from code |
| `/admin-api/role/:role/permissions` | GET | manage_roles | Role permissions |
| `/admin-api/role/:role/permissions/set` | POST | manage_roles | Set role perms |
| `/admin-api/role/:role/permissions/reset` | POST | manage_roles | Reset to defaults |
| `/admin-api/user/:id/permissions` | GET | manage_roles | User overrides |
| `/admin-api/user/:id/permissions/grant` | POST | manage_roles | Grant override |
| `/admin-api/user/:id/permissions/deny` | POST | manage_roles | Deny override |
| `/admin-api/user/:id/permissions/remove` | DELETE | manage_roles | Remove override |
| `/admin-api/user/:id/permissions/clear` | DELETE | manage_roles | Clear overrides |
| `/admin-api/settings` | GET | manage_settings | List settings |
| `/admin-api/settings/set` | POST | manage_settings | Set setting |
| `/admin-api/setting/:key` | GET | manage_settings | Get setting |
| `/admin-api/setting/:key/delete` | DELETE | manage_settings | Delete setting |
| `/admin-api/favorites` | GET | view_analytics | List favorites |
| `/admin-api/favorites/most` | GET | view_analytics | Most favorited |
| `/admin-api/stats/overview` | GET | view_analytics | Dashboard overview |
| `/admin-api/stats/staff` | GET | view_analytics | Staff stats |
| `/admin-api/stats/customers` | GET | view_analytics | Customer stats |
| `/admin-api/stats/categories` | GET | view_analytics | Category stats |
| `/admin-api/stats/products` | GET | view_analytics | Product stats |
| `/admin-api/stats/orders` | GET | view_analytics | Order stats |
| `/admin-api/stats/banners` | GET | view_analytics | Banner stats |
| `/admin-api/stats/coupons` | GET | view_analytics | Coupon stats |
| `/admin-api/stats/discounts` | GET | view_analytics | Discount stats |
| `/admin-api/stats/zones` | GET | view_analytics | Zone stats |
| `/admin-api/stats/reviews` | GET | view_analytics | Review stats |
| `/admin-api/stats/payments` | GET | view_analytics | Payment stats |
| `/admin-api/stats/notifications` | GET | view_analytics | Notification stats |
| `/admin-api/stats/favorites` | GET | view_analytics | Favorite stats |

---

## Order Status Flow

```
pending → confirmed → preparing → delivering → delivered → completed
   ↓
cancelled
```

- Admins/managers can advance orders through any valid transition
- Each transition is logged with timestamp, admin name, and optional note
- Cancellation requires a reason
- Courier assignment is independent of status

## Payment Status Flow

```
pending → processing → completed → refunded
              ↓
            failed
```

- Completing a payment auto-sets order payment_status to `paid`
- Refunding auto-sets order payment_status to `refunded`

## Session Info

- Sessions expire after **72 hours**
- Each login creates a new session (multiple devices supported)
- Use `logout-all` to invalidate all sessions
- Session key is a 64-character hex string
- Deleting a staff user invalidates all their sessions

## Default Role Permissions

| Role | Permissions |
|------|-------------|
| **admin** | All permissions |
| **manager** | manage: categories, products, banners, coupons, discounts, orders, notifications, delivery zones, reviews, payments. view: users, categories, products, orders, payments, analytics, delivery zones, reviews. assign_orders, update_order_status |
| **courier** | view_assigned_orders, update_order_status, view_delivery_zones |
| **client** | No admin permissions |
