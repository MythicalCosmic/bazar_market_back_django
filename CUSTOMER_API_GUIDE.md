# Bazar Market - Customer API Guide

**Base URL:** `https://api.bazarmarket.org/api`

All endpoints are prefixed with `/api/`. For example, to list products:
```
GET https://api.bazarmarket.org/api/products
```

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Catalog (Public)](#2-catalog-public)
3. [Cart](#3-cart)
4. [Addresses](#4-addresses)
5. [Orders](#5-orders)
6. [Favorites](#6-favorites)
7. [Reviews](#7-reviews)
8. [Notifications](#8-notifications)
9. [Referrals](#9-referrals)
10. [Coupons](#10-coupons)
11. [Banners (Public)](#11-banners-public)
12. [Delivery Check (Public)](#12-delivery-check-public)
13. [Error Handling](#13-error-handling)
14. [Rate Limiting](#14-rate-limiting)
15. [Pagination](#15-pagination)

---

## General Info

### Headers

All requests must include:
```
Content-Type: application/json
```

Protected endpoints also require:
```
Authorization: Bearer <session_key>
```

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
| 403 | Forbidden (e.g., phone not verified) |
| 404 | Resource not found |
| 405 | Method not allowed |
| 422 | Validation error |
| 429 | Rate limited |
| 500 | Server error |

---

## 1. Authentication

### 1.1 Register

Creates a new customer account and sends an OTP code to the phone number for verification.

```
POST /api/auth/register
```

**Rate limit:** 3 requests per minute

**Auth required:** No

**Body:**
```json
{
  "phone": "+998901234567",
  "first_name": "Aziza",
  "password": "mypassword123",
  "last_name": "Umarova",
  "language": "uz",
  "telegram_id": 123456789,
  "device": "iPhone 15"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone | string | Yes | Phone number in international format |
| first_name | string | Yes | First name |
| password | string | Yes | Minimum 6 characters |
| last_name | string | No | Last name (default: "") |
| language | string | No | `"uz"` or `"ru"` (default: `"uz"`) |
| telegram_id | integer | No | Telegram user ID |
| device | string | No | Device name for session tracking |

**Response (201):**
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "session_key": "a1b2c3d4e5f6...",
    "user": {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "phone": "+998901234567",
      "first_name": "Aziza",
      "last_name": "Umarova",
      "language": "uz",
      "is_phone_verified": false
    },
    "expires_at": "2026-05-02T12:00:00+05:00",
    "verification_sent": true
  }
}
```

**Important:** After registration, the user must verify their phone before they can place orders. Save the `session_key` — use it in the `Authorization` header for all protected requests.

**Errors:**
- `"Phone already registered"` — phone exists
- `"Password must be at least 6 characters"` — short password
- `"Invalid language"` — language not `uz` or `ru`

---

### 1.2 Login

```
POST /api/auth/login
```

**Rate limit:** 5 requests per minute

**Auth required:** No

**Body:**
```json
{
  "phone": "+998901234567",
  "password": "mypassword123",
  "device": "iPhone 15"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone | string | Yes | Registered phone number |
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
      "phone": "+998901234567",
      "first_name": "Aziza",
      "last_name": "Umarova",
      "language": "uz",
      "is_phone_verified": true
    },
    "expires_at": "2026-05-02T12:00:00+05:00"
  }
}
```

**Errors:**
- `"User not found"` — phone not registered
- `"Account is deactivated"` — account disabled by admin
- `"Invalid credentials"` — wrong password

---

### 1.3 Verify Phone

After registration, the user receives an SMS with a 6-digit OTP code. Use this endpoint to verify.

```
POST /api/auth/verify
```

**Auth required:** Yes

**Body:**
```json
{
  "code": "123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "message": "Phone verified",
    "is_phone_verified": true
  }
}
```

**Errors:**
- `"Phone already verified"` — already done
- `"Code must be 6 digits"` — invalid code format
- `"Invalid or expired code"` — wrong OTP or expired (2 min TTL)

---

### 1.4 Resend Verification Code

Request a new OTP code.

```
POST /api/auth/resend-code
```

**Rate limit:** 1 request per minute

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": {
    "message": "Verification code sent",
    "expires_in": 120
  }
}
```

---

### 1.5 Get Profile

```
GET /api/auth/me
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "phone": "+998901234567",
    "first_name": "Aziza",
    "last_name": "Umarova",
    "language": "uz",
    "is_phone_verified": true,
    "created_at": "2026-04-29T10:00:00+05:00"
  }
}
```

---

### 1.6 Update Profile

```
PATCH /api/auth/me/update
```

**Auth required:** Yes

**Body:** Only send the fields you want to change.
```json
{
  "first_name": "Aziza",
  "last_name": "Karimova",
  "language": "ru",
  "phone": "+998901234568",
  "password": "newpassword123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| first_name | string | No | New first name |
| last_name | string | No | New last name |
| language | string | No | `"uz"` or `"ru"` |
| phone | string | No | New phone number (must be unique) |
| password | string | No | New password (min 6 chars) |

**Response (200):**
```json
{
  "success": true,
  "message": "Profile updated",
  "data": {
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "phone": "+998901234568",
    "first_name": "Aziza",
    "last_name": "Karimova",
    "language": "ru",
    "is_phone_verified": true,
    "created_at": "2026-04-29T10:00:00+05:00"
  }
}
```

---

### 1.7 Logout

Logout from current device only.

```
POST /api/auth/logout
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Logged out" }
}
```

---

### 1.8 Logout All Devices

```
POST /api/auth/logout-all
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Logged out from all devices" }
}
```

---

### 1.9 Delete Account

Soft-deletes the account and invalidates all sessions.

```
POST /api/auth/me/delete
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Account deleted" }
}
```

---

## 2. Catalog (Public)

These endpoints are public — no authentication required. Rate limited to 60 req/min per IP (search: 30/min).

### 2.1 List Products

```
GET /api/products
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| category_id | integer | — | Filter by category |
| q | string | — | Search by name/description |
| is_featured | string | — | `"true"` for featured only |
| order_by | string | `"sort_order"` | `sort_order`, `price`, `-price`, `name_uz`, `-created_at` |
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page (max 100) |

**Example:** `GET /api/products?category_id=5&order_by=-price&page=1&per_page=10`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "uuid": "550e8400-...",
        "name_uz": "Olma",
        "name_ru": "Яблоко",
        "price": "15000.00",
        "unit": "kg",
        "in_stock": true,
        "is_featured": false,
        "category_id": 5,
        "category_name": "Mevalar",
        "image": "https://example.com/olma.jpg",
        "discounted_price": "12750.00"
      }
    ],
    "page": 1,
    "per_page": 10,
    "total": 45,
    "total_pages": 5
  }
}
```

**Notes:**
- `image` — primary image URL, may be absent if no images uploaded
- `discounted_price` — only present when an active discount applies. If absent, the product has no discount
- `unit` — one of: `"kg"`, `"piece"`, `"liter"`, `"pack"`, `"bundle"`

---

### 2.2 Get Product Detail

```
GET /api/product/{product_id}
```

**Example:** `GET /api/product/1`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "uuid": "550e8400-...",
    "name_uz": "Olma",
    "name_ru": "Яблоко",
    "price": "15000.00",
    "unit": "kg",
    "in_stock": true,
    "is_featured": false,
    "category_id": 5,
    "category_name": "Mevalar",
    "image": "https://example.com/olma.jpg",
    "description_uz": "Toshkent olmasi, yangi yig'ilgan",
    "description_ru": "Ташкентские яблоки, свежесобранные",
    "step": "0.500",
    "min_qty": "0.500",
    "max_qty": null,
    "stock_qty": "150.000",
    "sku": "FRU-APPLE-001",
    "images": [
      { "id": 1, "image": "https://example.com/olma.jpg", "is_primary": true },
      { "id": 2, "image": "https://example.com/olma-2.jpg", "is_primary": false }
    ],
    "discounts": [
      {
        "id": 3,
        "name": "Mevalar chegirma",
        "type": "percent",
        "value": "15.00"
      }
    ],
    "discounted_price": "12750.00"
  }
}
```

**Notes:**
- `step` — quantity increment. `"0.500"` means user can buy 0.5, 1.0, 1.5 kg, etc.
- `min_qty` — minimum order quantity
- `max_qty` — maximum order quantity per item. `null` = unlimited
- `stock_qty` — available stock. `null` = unlimited stock
- `discounts` — list of currently active discounts. May be empty `[]`
- `discounted_price` — best price after applying the most favorable discount. Only present if discounts exist

---

### 2.3 List Categories

Returns all active categories (flat list).

```
GET /api/categories
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "id": 1, "name_uz": "Mevalar", "name_ru": "Фрукты", "image": "https://...", "product_count": 6 },
    { "id": 2, "name_uz": "Sabzavotlar", "name_ru": "Овощи", "image": "", "product_count": 8 }
  ]
}
```

---

### 2.4 Category Tree

Returns categories in a hierarchical tree structure.

```
GET /api/categories/tree
```

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name_uz": "Mevalar",
      "name_ru": "Фрукты",
      "image": "https://...",
      "product_count": 0,
      "children": [
        { "id": 5, "name_uz": "Olma", "name_ru": "Яблоки", "image": "", "product_count": 3, "children": [] },
        { "id": 6, "name_uz": "Banan", "name_ru": "Бананы", "image": "", "product_count": 2, "children": [] }
      ]
    }
  ]
}
```

---

### 2.5 Featured Products

```
GET /api/products/featured
```

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page |

**Response:** Same paginated format as [List Products](#21-list-products).

---

### 2.6 Popular Products

Products ordered by total units sold (from completed/delivered orders).

```
GET /api/products/popular
```

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page |

**Response:** Same paginated format as List Products. Each item may include `"total_sold": "150.000"`.

---

### 2.7 Search Products

```
GET /api/products/search?q=olma
```

**Rate limit:** 30 requests per minute

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| q | string | Yes | Search query (searches name and description in both uz/ru) |
| page | integer | No | Page number (default: 1) |
| per_page | integer | No | Items per page (default: 20) |

**Response:** Same paginated format as List Products.

---

## 3. Cart

All cart endpoints require authentication. The cart is per-user and persists across sessions.

### 3.1 Get Cart

```
GET /api/cart
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "product_id": 1,
        "name_uz": "Olma",
        "name_ru": "Яблоко",
        "unit": "kg",
        "price": "15000.00",
        "quantity": "2.000",
        "total": "30000.00",
        "in_stock": true,
        "image": "https://example.com/olma.jpg"
      },
      {
        "product_id": 7,
        "name_uz": "Sut",
        "name_ru": "Молоко",
        "unit": "liter",
        "price": "12000.00",
        "quantity": "1.000",
        "total": "12000.00",
        "in_stock": true,
        "image": null
      }
    ],
    "item_count": 2,
    "subtotal": "42000.00"
  }
}
```

---

### 3.2 Add to Cart

```
POST /api/cart/add
```

**Auth required:** Yes

**Body:**
```json
{
  "product_id": 1,
  "quantity": "1.5"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| product_id | integer | Yes | Product ID |
| quantity | string/number | Yes | Quantity to add. Must respect the product's `step`, `min_qty`, `max_qty`, and available `stock_qty` |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "message": "Added to cart",
    "product_id": 1,
    "quantity": "1.500"
  }
}
```

**Errors:**
- `"Product not found"` — invalid product ID or product is inactive
- `"Product is out of stock"` — product unavailable
- `"Quantity must be positive"` — quantity <= 0
- `"Minimum quantity is 0.500"` — below min_qty
- `"Maximum quantity is 10.000"` — above max_qty
- `"Quantity must be in steps of 0.500"` — not a valid step
- `"Only 5.000 available in stock"` — exceeds stock

---

### 3.3 Update Cart Item

```
POST /api/cart/update
```

**Auth required:** Yes

**Body:**
```json
{
  "product_id": 1,
  "quantity": "2.5"
}
```

Same validation rules as Add to Cart. Setting `quantity` to `0` or negative removes the item.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "message": "Cart updated",
    "product_id": 1,
    "quantity": "2.500"
  }
}
```

---

### 3.4 Remove Cart Item

```
POST /api/cart/remove
```

**Auth required:** Yes

**Body:**
```json
{
  "product_id": 1
}
```

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Item removed from cart" }
}
```

---

### 3.5 Clear Cart

Removes all items.

```
POST /api/cart/clear
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Cart cleared (3 items removed)" }
}
```

---

## 4. Addresses

### 4.1 List Addresses

```
GET /api/addresses
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "label": "Uy",
      "address_text": "Chilanzar 9, dom 45",
      "latitude": "41.2856000",
      "longitude": "69.2042000",
      "entrance": "2",
      "floor": "3",
      "apartment": "15",
      "comment": "Qo'ng'iroq qiling",
      "is_default": true
    },
    {
      "id": 2,
      "label": "Ish",
      "address_text": "Amir Temur ko'chasi 108",
      "latitude": "41.3111000",
      "longitude": "69.2797000",
      "entrance": "",
      "floor": "",
      "apartment": "",
      "comment": "",
      "is_default": false
    }
  ]
}
```

---

### 4.2 Add Address

```
POST /api/address/add
```

**Auth required:** Yes

**Body:**
```json
{
  "latitude": 41.2856,
  "longitude": 69.2042,
  "address_text": "Chilanzar 9, dom 45",
  "label": "Uy",
  "entrance": "2",
  "floor": "3",
  "apartment": "15",
  "comment": "Qo'ng'iroq qiling",
  "is_default": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| latitude | number | Yes | Latitude coordinate |
| longitude | number | Yes | Longitude coordinate |
| address_text | string | Yes | Human-readable address |
| label | string | No | Label like "Uy", "Ish" |
| entrance | string | No | Entrance/podezd number |
| floor | string | No | Floor number |
| apartment | string | No | Apartment number |
| comment | string | No | Delivery instructions |
| is_default | boolean | No | Set as default address (default: false) |

**Response (201):**
```json
{
  "success": true,
  "message": "Address added",
  "data": {
    "id": 3,
    "address_text": "Chilanzar 9, dom 45"
  }
}
```

---

### 4.3 Update Address

```
PATCH /api/address/{address_id}/update
```

**Auth required:** Yes

**Body:** Send only the fields you want to change.
```json
{
  "label": "Yangi uy",
  "apartment": "22"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Address updated",
  "data": {
    "id": 3,
    "address_text": "Chilanzar 9, dom 45"
  }
}
```

---

### 4.4 Delete Address

```
POST /api/address/{address_id}/delete
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Address deleted" }
}
```

---

### 4.5 Set Default Address

```
POST /api/address/{address_id}/default
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Default address updated" }
}
```

---

## 5. Orders

### 5.1 Place Order

Creates an order from the current cart contents. Requires phone verification.

```
POST /api/orders/place
```

**Rate limit:** 10 requests per minute

**Auth required:** Yes (phone must be verified)

**Body:**
```json
{
  "address_id": 1,
  "payment_method": "cash",
  "coupon_code": "YANGI2026",
  "user_note": "Iltimos tez yetkazib bering",
  "scheduled_time": "2026-04-30T14:00:00"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| address_id | integer | Yes | Delivery address ID (must belong to user) |
| payment_method | string | Yes | `"cash"` or `"card"` |
| coupon_code | string | No | Coupon code for discount |
| user_note | string | No | Note for delivery |
| scheduled_time | string | No | ISO 8601 datetime for scheduled delivery. `null` = ASAP |

**Response (201):**
```json
{
  "success": true,
  "message": "Order placed successfully",
  "data": {
    "order_id": 42,
    "order_number": "ORD-20260429-0042",
    "status": "pending",
    "subtotal": "42000.00",
    "delivery_fee": "10000.00",
    "discount": "4200.00",
    "total": "47800.00",
    "payment_method": "cash"
  }
}
```

**What happens:**
1. Cart items are validated (active, in stock)
2. Discounted prices are calculated from active product/category discounts
3. Delivery fee is fetched from system settings
4. Minimum order total is enforced
5. Coupon is validated and applied (if provided)
6. Order + order items are created
7. Stock is deducted
8. Cart is cleared
9. Admin is notified

**Errors:**
- `"Phone verification required before placing orders"` (403) — verify phone first
- `"Cart is empty"` — nothing to order
- `"Address not found"` — invalid or doesn't belong to user
- `"Invalid payment method"` — not `cash` or `card`
- `"Product X is no longer available"` — product deleted/deactivated
- `"Product X is out of stock"` — stock depleted
- `"Minimum order total is 30000 UZS"` — subtotal too low
- Coupon errors (expired, limit reached, etc.)

---

### 5.2 List Orders

```
GET /api/orders
```

**Auth required:** Yes

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| status | string | — | Filter: `pending`, `confirmed`, `preparing`, `delivering`, `delivered`, `completed`, `cancelled` |
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page |

**Example:** `GET /api/orders?status=pending&page=1`

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 42,
        "uuid": "550e8400-...",
        "order_number": "ORD-20260429-0042",
        "status": "pending",
        "subtotal": "42000.00",
        "delivery_fee": "10000.00",
        "discount": "4200.00",
        "total": "47800.00",
        "payment_method": "cash",
        "payment_status": "unpaid",
        "delivery_address_text": "Chilanzar 9, dom 45",
        "user_note": "Iltimos tez yetkazib bering",
        "scheduled_time": null,
        "created_at": "2026-04-29T12:00:00+05:00",
        "confirmed_at": null,
        "preparing_at": null,
        "delivering_at": null,
        "delivered_at": null,
        "completed_at": null,
        "cancelled_at": null
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

---

### 5.3 Get Order Detail

```
GET /api/order/{order_id}
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": 42,
    "uuid": "550e8400-...",
    "order_number": "ORD-20260429-0042",
    "status": "confirmed",
    "subtotal": "42000.00",
    "delivery_fee": "10000.00",
    "discount": "4200.00",
    "total": "47800.00",
    "payment_method": "cash",
    "payment_status": "unpaid",
    "delivery_address_text": "Chilanzar 9, dom 45",
    "user_note": "Iltimos tez yetkazib bering",
    "scheduled_time": null,
    "created_at": "2026-04-29T12:00:00+05:00",
    "confirmed_at": "2026-04-29T12:05:00+05:00",
    "preparing_at": null,
    "delivering_at": null,
    "delivered_at": null,
    "completed_at": null,
    "cancelled_at": null,
    "items": [
      {
        "product_id": 1,
        "product_name": "Olma",
        "unit": "kg",
        "unit_price": "12750.00",
        "quantity": "2.000",
        "total": "25500.00"
      },
      {
        "product_id": 7,
        "product_name": "Sut",
        "unit": "liter",
        "unit_price": "12000.00",
        "quantity": "1.000",
        "total": "12000.00"
      }
    ],
    "status_log": [
      {
        "from_status": "",
        "to_status": "pending",
        "note": "",
        "created_at": "2026-04-29T12:00:00+05:00"
      },
      {
        "from_status": "pending",
        "to_status": "confirmed",
        "note": "Accepted and printing",
        "created_at": "2026-04-29T12:05:00+05:00"
      }
    ]
  }
}
```

**Notes:**
- `unit_price` in order items is the price at order time (may include discount). This is frozen and won't change.
- `status_log` shows the full timeline of status changes

---

### 5.4 Active Orders

Returns orders with status: `pending`, `confirmed`, `preparing`, or `delivering`.

```
GET /api/orders/active
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 42,
      "order_number": "ORD-20260429-0042",
      "status": "delivering",
      "total": "47800.00",
      "created_at": "2026-04-29T12:00:00+05:00",
      ...
    }
  ]
}
```

---

### 5.5 Cancel Order

Only orders with status `"pending"` can be cancelled.

```
POST /api/order/{order_id}/cancel
```

**Auth required:** Yes

**Body (optional):**
```json
{
  "reason": "Boshqa manzilga kerak"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "order_id": 42,
    "status": "cancelled"
  }
}
```

**What happens on cancel:**
- Order status set to `cancelled`
- Stock is restored for all items
- Coupon usage is decremented (if coupon was used)

**Errors:**
- `"Order not found"` — doesn't exist or doesn't belong to user
- `"Only pending orders can be cancelled"` — order already confirmed/in progress

---

### 5.6 Reorder

Adds items from a previous order back to the cart.

```
POST /api/order/{order_id}/reorder
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": {
    "added": [
      { "product_id": 1, "name": "Olma", "quantity": "2.000" },
      { "product_id": 7, "name": "Sut", "quantity": "1.000" }
    ],
    "skipped": [
      { "product_id": 15, "name": "Anor", "reason": "Out of stock" }
    ],
    "message": "2 items added to cart, 1 skipped"
  }
}
```

---

## 6. Favorites

### 6.1 List Favorites

```
GET /api/favorites
```

**Auth required:** Yes

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "product_id": 1,
        "name_uz": "Olma",
        "name_ru": "Яблоко",
        "price": "15000.00",
        "unit": "kg",
        "in_stock": true,
        "created_at": "2026-04-29T10:00:00+05:00"
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

---

### 6.2 Toggle Favorite

Add or remove a product from favorites. If already favorited, removes it. If not, adds it.

```
POST /api/favorite/{product_id}/toggle
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": {
    "product_id": 1,
    "is_favorited": true
  }
}
```

---

### 6.3 Check Favorite

Check if a specific product is in the user's favorites.

```
GET /api/favorite/{product_id}/check
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": {
    "product_id": 1,
    "is_favorited": true
  }
}
```

---

## 7. Reviews

### 7.1 Submit Review

Can only review orders with status `"delivered"` or `"completed"`. One review per order.

```
POST /api/review/submit
```

**Auth required:** Yes

**Body:**
```json
{
  "order_id": 42,
  "rating": 5,
  "comment": "Juda yaxshi xizmat!"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| order_id | integer | Yes | Order ID to review |
| rating | integer | Yes | 1 to 5 |
| comment | string | No | Review text |

**Response (201):**
```json
{
  "success": true,
  "message": "Review submitted",
  "data": {
    "id": 10,
    "message": "Review submitted"
  }
}
```

**Notes:** Reviews go through moderation. `moderation_status` starts as `"pending"`.

**Errors:**
- `"Order not found"` — invalid order or not the user's
- `"Can only review delivered or completed orders"`
- `"You have already reviewed this order"`
- `"Rating must be between 1 and 5"`

---

### 7.2 List My Reviews

```
GET /api/reviews
```

**Auth required:** Yes

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 10,
        "order_id": 42,
        "order_number": "ORD-20260429-0042",
        "rating": 5,
        "comment": "Juda yaxshi xizmat!",
        "admin_reply": "Rahmat!",
        "moderation_status": "approved",
        "created_at": "2026-04-29T15:00:00+05:00"
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

---

## 8. Notifications

### 8.1 List Notifications

```
GET /api/notifications
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 5,
        "type": "order_status",
        "title": "Buyurtma tasdiqlandi",
        "body": "ORD-20260429-0042 raqamli buyurtmangiz tasdiqlandi",
        "payload": { "order_id": 42 },
        "channel": "telegram",
        "is_read": false,
        "sent_at": "2026-04-29T12:05:00+05:00"
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 1,
    "total_pages": 1
  }
}
```

**Notes:**
- `type` — `"order_status"`, `"promo"`, or `"system"`
- `channel` — `"telegram"`, `"sms"`, or `"push"`
- `payload` — arbitrary JSON for deep linking (e.g., `{"order_id": 42}`)

---

### 8.2 Mark Notification as Read

```
POST /api/notification/{notification_id}/read
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Marked as read" }
}
```

---

### 8.3 Mark All as Read

```
POST /api/notifications/read-all
```

**Auth required:** Yes

**Body:** empty

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "3 notifications marked as read" }
}
```

---

### 8.4 Unread Count

```
GET /api/notifications/unread-count
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": { "unread_count": 3 }
}
```

---

## 9. Referrals

### 9.1 Get My Referral Info

```
GET /api/referral
```

**Auth required:** Yes

**Response (200):**
```json
{
  "success": true,
  "data": {
    "referral_code": "550E8400",
    "referral_link": "https://t.me/BazarMarketBot?start=ref_550E8400",
    "total_referrals": 3,
    "total_rewards": "45000.00",
    "reward_info": {
      "type": "fixed",
      "value": "15000",
      "description": "Invite friends and earn 15000 UZS per referral"
    }
  }
}
```

**Notes:**
- `referral_code` is derived from the user's UUID (first 8 chars, uppercase)
- `referral_link` deep-links into the Telegram bot with the referral code
- When a referred user completes their first order, the referrer gets a coupon

---

### 9.2 List My Referrals

```
GET /api/referral/list
```

**Auth required:** Yes

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number |
| per_page | integer | 20 | Items per page |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "referred_name": "Bekzod",
        "reward_amount": "15000.00",
        "is_rewarded": true,
        "created_at": "2026-04-25T10:00:00+05:00"
      },
      {
        "id": 2,
        "referred_name": "Charos",
        "reward_amount": "15000.00",
        "is_rewarded": false,
        "created_at": "2026-04-28T14:00:00+05:00"
      }
    ],
    "page": 1,
    "per_page": 20,
    "total": 2,
    "total_pages": 1
  }
}
```

**Notes:**
- `is_rewarded: false` — the referred user hasn't completed their first order yet

---

### 9.3 Apply Referral Code

Apply someone else's referral code to your account. Can only be done once.

```
POST /api/referral/apply
```

**Auth required:** Yes

**Body:**
```json
{
  "referral_code": "A3B4C5D6"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": { "message": "Referral applied successfully" }
}
```

**Errors:**
- `"You have already been referred"` — already used a referral
- `"Invalid referral code"` — code doesn't match any user
- `"You cannot refer yourself"`

---

## 10. Coupons

### 10.1 Validate Coupon

Check if a coupon is valid and calculate the discount. Call this before placing an order to show the user how much they'll save.

```
POST /api/coupon/validate
```

**Auth required:** Yes

**Body:**
```json
{
  "code": "YANGI2026",
  "subtotal": 100000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | string | Yes | Coupon code |
| subtotal | number | Yes | Cart subtotal to calculate discount against |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "code": "YANGI2026",
    "type": "percent",
    "value": "10.00",
    "discount_amount": "10000.00",
    "max_discount": "20000.00"
  }
}
```

**Notes:**
- `type` — `"percent"` or `"fixed"`
- `discount_amount` — the actual discount that will be applied
- For percent coupons, `max_discount` caps the discount. E.g., 10% of 500,000 = 50,000 but max_discount 20,000 caps it

**Errors:**
- `"Coupon not found"` — code doesn't exist
- `"Coupon is not active"`
- `"Coupon has not started yet"`
- `"Coupon has expired"`
- `"Coupon usage limit reached"`
- `"You have already used this coupon X times"`
- `"Minimum order amount is 200000.00"`

---

## 11. Banners (Public)

```
GET /api/banners
```

**Rate limit:** 60 requests per minute

**Auth required:** No

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Yangi mahsulotlar!",
      "image": "https://example.com/banner1.jpg",
      "link_type": "category",
      "link_value": "5"
    },
    {
      "id": 2,
      "title": "Chegirma 20%",
      "image": "https://example.com/banner2.jpg",
      "link_type": "product",
      "link_value": "12"
    },
    {
      "id": 3,
      "title": "Bepul yetkazib berish",
      "image": "https://example.com/banner3.jpg",
      "link_type": "url",
      "link_value": "https://example.com/promo"
    }
  ]
}
```

**Notes on `link_type`:**

| link_type | link_value | Frontend action |
|-----------|------------|-----------------|
| `"category"` | category ID | Navigate to category page |
| `"product"` | product ID | Navigate to product detail |
| `"url"` | URL string | Open URL in browser/webview |
| `"none"` | `""` | No action (display only) |

---

## 12. Delivery Check (Public)

Check if delivery is available for a given location.

```
GET /api/delivery/check?lat=41.2856&lng=69.2042
```

**Rate limit:** 30 requests per minute

**Auth required:** No

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| lat | number | Yes | Latitude |
| lng | number | Yes | Longitude |

**Response — delivery available (200):**
```json
{
  "success": true,
  "data": {
    "available": true,
    "zone": {
      "id": 1,
      "name": "Chilanzar",
      "delivery_fee": "10000.00",
      "min_order": "50000.00",
      "estimated_minutes": 30
    }
  }
}
```

**Response — delivery not available (200):**
```json
{
  "success": true,
  "data": {
    "available": false
  }
}
```

---

## 13. Error Handling

All errors return the same structure:

```json
{
  "success": false,
  "message": "Error description"
}
```

### Common Errors

**401 — Not Authenticated:**
```json
{
  "success": false,
  "message": "Authorization header required"
}
```
The `Authorization: Bearer <session_key>` header is missing or invalid.

**401 — Expired Session:**
```json
{
  "success": false,
  "message": "Invalid or expired session"
}
```
The session has expired (72h TTL). Re-login to get a new session key.

**403 — Phone Not Verified:**
```json
{
  "success": false,
  "message": "Phone verification required before placing orders"
}
```
Only returned by the Place Order endpoint.

**404 — Not Found:**
```json
{
  "success": false,
  "message": "Product not found"
}
```

**405 — Method Not Allowed:**
```json
{
  "success": false,
  "message": "Method not allowed"
}
```
You sent GET to a POST-only endpoint, etc.

**422 — Validation Error:**
```json
{
  "success": false,
  "message": "Missing required fields: phone, first_name"
}
```

**429 — Rate Limited:**
```json
{
  "success": false,
  "message": "Too many requests. Please try again later."
}
```
Check the `Retry-After` response header (in seconds) for when to retry.

---

## 14. Rate Limiting

Rate limits are per IP address. When exceeded, the API returns `429` with a `Retry-After` header.

| Endpoint | Limit |
|----------|-------|
| `POST /api/auth/register` | 3/min |
| `POST /api/auth/login` | 5/min |
| `POST /api/auth/resend-code` | 1/min |
| `POST /api/orders/place` | 10/min |
| `GET /api/products/search` | 30/min |
| `GET /api/delivery/check` | 30/min |
| All other catalog/banner endpoints | 60/min |
| All other authenticated endpoints | No limit |

---

## 15. Pagination

All list endpoints that return multiple items use consistent pagination:

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

**Non-paginated lists** (addresses, active orders, banners, categories) return a plain array in `data`.

---

## Quick Reference Table

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | No | Register new account |
| `/api/auth/login` | POST | No | Login |
| `/api/auth/verify` | POST | Yes | Verify phone with OTP |
| `/api/auth/resend-code` | POST | Yes | Resend OTP |
| `/api/auth/me` | GET | Yes | Get profile |
| `/api/auth/me/update` | PATCH | Yes | Update profile |
| `/api/auth/logout` | POST | Yes | Logout |
| `/api/auth/logout-all` | POST | Yes | Logout all devices |
| `/api/auth/me/delete` | POST | Yes | Delete account |
| `/api/products` | GET | No | List products |
| `/api/product/:id` | GET | No | Product detail |
| `/api/products/featured` | GET | No | Featured products |
| `/api/products/popular` | GET | No | Popular products |
| `/api/products/search` | GET | No | Search products |
| `/api/categories` | GET | No | List categories |
| `/api/categories/tree` | GET | No | Category tree |
| `/api/cart` | GET | Yes | View cart |
| `/api/cart/add` | POST | Yes | Add to cart |
| `/api/cart/update` | POST | Yes | Update quantity |
| `/api/cart/remove` | POST | Yes | Remove item |
| `/api/cart/clear` | POST | Yes | Clear cart |
| `/api/addresses` | GET | Yes | List addresses |
| `/api/address/add` | POST | Yes | Add address |
| `/api/address/:id/update` | PATCH | Yes | Update address |
| `/api/address/:id/delete` | POST | Yes | Delete address |
| `/api/address/:id/default` | POST | Yes | Set default |
| `/api/orders` | GET | Yes | List orders |
| `/api/orders/active` | GET | Yes | Active orders |
| `/api/orders/place` | POST | Yes | Place order |
| `/api/order/:id` | GET | Yes | Order detail |
| `/api/order/:id/cancel` | POST | Yes | Cancel order |
| `/api/order/:id/reorder` | POST | Yes | Reorder |
| `/api/favorites` | GET | Yes | List favorites |
| `/api/favorite/:id/toggle` | POST | Yes | Toggle favorite |
| `/api/favorite/:id/check` | GET | Yes | Check if favorited |
| `/api/reviews` | GET | Yes | List my reviews |
| `/api/review/submit` | POST | Yes | Submit review |
| `/api/notifications` | GET | Yes | List notifications |
| `/api/notification/:id/read` | POST | Yes | Mark as read |
| `/api/notifications/read-all` | POST | Yes | Mark all read |
| `/api/notifications/unread-count` | GET | Yes | Unread count |
| `/api/referral` | GET | Yes | My referral info |
| `/api/referral/list` | GET | Yes | My referrals |
| `/api/referral/apply` | POST | Yes | Apply referral code |
| `/api/coupon/validate` | POST | Yes | Validate coupon |
| `/api/banners` | GET | No | Active banners |
| `/api/delivery/check` | GET | No | Check delivery zone |

---

## Order Status Flow

```
pending → confirmed → preparing → delivering → delivered → completed
   ↓
cancelled
```

- Customers can only cancel orders in `pending` status
- Status transitions are managed by admin/system
- Each transition is logged in `status_log`

## Session Info

- Sessions expire after **72 hours**
- Each login creates a new session (multiple devices supported)
- Use `logout-all` to invalidate all sessions (e.g., password change)
- Session key is a 64-character hex string
