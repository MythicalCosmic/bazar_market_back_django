# Auth Flow Change — Registration & Forgot Password

## What Changed

Registration no longer creates a user immediately. The user is created **only after phone verification**. Registration data is held in Redis cache until OTP is confirmed. This eliminates the "phone already registered" dead-end when a user disconnects mid-registration.

A forgot/reset password flow has been added.

---

## New Registration Flow

**Before:** `register` → user created → `verify` → flag set
**Now:** `register` → OTP sent, data cached → `verify` → user created + session returned

### Step 1: Register (sends OTP, no user created yet)
```
POST /api/auth/register
Content-Type: application/json

{
  "phone": "+998901234567",
  "first_name": "Ali",
  "password": "secret123",
  "last_name": "",
  "language": "uz"
}
```

Response:
```json
{
  "success": true,
  "message": "Verification code sent",
  "data": {
    "phone": "+998901234567",
    "verification_sent": true,
    "expires_in": 120
  }
}
```

**No `session_key` returned here.** The user is not logged in yet.

### Step 2: Verify & complete registration
```
POST /api/auth/register/verify
Content-Type: application/json

{
  "phone": "+998901234567",
  "code": "123456",
  "device": "iOS App"
}
```

Response (user created now):
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "session_key": "abc123...",
    "user": {
      "id": 1,
      "phone": "+998901234567",
      "first_name": "Ali",
      "is_phone_verified": true
    },
    "expires_at": "2026-06-02T..."
  }
}
```

Save `session_key` — user is now logged in.

### Resend OTP (during registration)
```
POST /api/auth/register/resend
Content-Type: application/json

{"phone": "+998901234567"}
```

Rate limited to 1 per 60 seconds.

### Edge Cases

| Scenario | What happens |
|---|---|
| User closes app before verifying | No user created. They can register again with the same phone. |
| OTP expires (2 min) | Registration data is gone. User re-submits `/register`. |
| User enters wrong code | Error: "Invalid or expired verification code". They can retry. |
| Someone else tries the same phone while pending | OTP won't match. No conflict. |

---

## Forgot Password Flow

### Step 1: Request reset code
```
POST /api/auth/forgot-password
Content-Type: application/json

{"phone": "+998901234567"}
```

Response:
```json
{
  "success": true,
  "data": {
    "message": "Reset code sent",
    "expires_in": 120
  }
}
```

### Step 2: Reset password with code
```
POST /api/auth/reset-password
Content-Type: application/json

{
  "phone": "+998901234567",
  "code": "654321",
  "new_password": "newsecret123"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "message": "Password reset successful. Please log in."
  }
}
```

All existing sessions are killed on reset. Redirect to login.

---

## Removed Endpoints

These no longer exist:
- ~~`POST /api/auth/verify`~~ — replaced by `/api/auth/register/verify`
- ~~`POST /api/auth/resend-code`~~ — replaced by `/api/auth/register/resend`

## Unchanged Endpoints

These work exactly as before:
- `POST /api/auth/login` — phone + password
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/me`
- `PATCH /api/auth/me/update`
- `POST /api/auth/me/delete`

---

## Frontend Checklist

- [ ] Registration screen: after `/register`, show OTP input (not home screen)
- [ ] Store `phone` from register response — needed for `/register/verify` and `/register/resend`
- [ ] Don't store `session_key` until `/register/verify` succeeds
- [ ] Show countdown timer (120s) on OTP screen with resend button
- [ ] Add "Forgot password?" link on login screen → phone input → OTP → new password
- [ ] After password reset, redirect to login (don't auto-login)
- [ ] Remove any references to old `/auth/verify` and `/auth/resend-code` endpoints

---

# Referral Reward System — Frontend Integration Guide

## What Changed

The referral system now supports **3 reward types** instead of only coupons. Admins create reward templates and activate one at a time. When a referred user completes their first order, the referrer automatically receives the active reward.

### Reward Types

| Type | What the referrer gets |
|---|---|
| **Coupon** | A one-time discount coupon (percent or fixed) |
| **Free Delivery** | N orders with delivery fee = 0 |
| **Bonus Product** | A specific product added for free on their next order |

---

## Admin Panel (admin-api)

### New Endpoints

All require `Authorization: Bearer {session_key}` and `manage_referral_rewards` permission.

#### List Rewards
```
GET /admin-api/referral-rewards?page=1&per_page=20&order_by=-created_at
```

#### Get Reward Detail
```
GET /admin-api/referral-reward/{id}
```

#### Create Reward

```
POST /admin-api/referral-reward/create
Content-Type: application/json
```

**Coupon example:**
```json
{
  "name": "10% off coupon",
  "type": "coupon",
  "coupon_type": "percent",
  "coupon_value": 10,
  "coupon_max_discount": 20000,
  "coupon_min_order": 50000,
  "coupon_expires_days": 30,
  "is_active": true
}
```

**Free delivery example:**
```json
{
  "name": "2 free deliveries",
  "type": "free_delivery",
  "free_delivery_count": 2,
  "is_active": false
}
```

**Bonus product example:**
```json
{
  "name": "Free 1kg apples",
  "type": "bonus_product",
  "bonus_product_id": 42,
  "bonus_quantity": "1",
  "is_active": false
}
```

#### Update Reward
```
PATCH /admin-api/referral-reward/{id}/update
Content-Type: application/json

{"name": "Updated name", "coupon_value": 15}
```

#### Delete Reward
```
DELETE /admin-api/referral-reward/{id}/delete
```

#### Activate / Deactivate
```
POST /admin-api/referral-reward/{id}/activate
POST /admin-api/referral-reward/{id}/deactivate
```

**Important:** Only one reward can be active at a time. Activating one automatically deactivates all others.

### Response Format

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "10% off coupon",
    "type": "coupon",
    "is_active": true,
    "created_at": "2026-05-01T12:00:00+05:00",
    "coupon_type": "percent",
    "coupon_value": "10.00",
    "coupon_max_discount": "20000.00",
    "coupon_min_order": "50000.00",
    "coupon_expires_days": 30
  }
}
```

Type-specific fields are only included for that type:
- `type: "coupon"` → `coupon_type`, `coupon_value`, `coupon_max_discount`, `coupon_min_order`, `coupon_expires_days`
- `type: "free_delivery"` → `free_delivery_count`
- `type: "bonus_product"` → `bonus_product_id`, `bonus_product_name`, `bonus_quantity`

### What the Admin Panel Should Do

1. **Referral Rewards page** — CRUD table showing all reward templates with a clear "Active" badge on the current one.
2. **Create form** — Show/hide fields based on selected `type`:
   - Coupon: show coupon_type, coupon_value, coupon_max_discount, coupon_min_order, coupon_expires_days
   - Free delivery: show free_delivery_count
   - Bonus product: show product picker + bonus_quantity
3. **Activate button** — Only one can be active. Show confirmation: "This will deactivate the current reward."
4. **Product picker** — For bonus_product type, use your existing product search/select component to pick `bonus_product_id`.

---

## Customer App (api)

### New Endpoint

#### My Rewards
```
GET /api/rewards
Authorization: Bearer {session_key}
```

Returns all active (unused) rewards for the logged-in user:

```json
{
  "success": true,
  "data": [
    {
      "id": 5,
      "type": "coupon",
      "is_used": false,
      "expires_at": "2026-06-01T12:00:00+05:00",
      "created_at": "2026-05-01T12:00:00+05:00",
      "coupon_code": "REF-4D8A2C1F"
    },
    {
      "id": 6,
      "type": "free_delivery",
      "is_used": false,
      "expires_at": null,
      "created_at": "2026-05-01T12:00:00+05:00",
      "free_deliveries_remaining": 2
    },
    {
      "id": 7,
      "type": "bonus_product",
      "is_used": false,
      "expires_at": null,
      "created_at": "2026-05-01T12:00:00+05:00",
      "bonus_claimed": false,
      "bonus_quantity": "1.000",
      "product_name": "Olma",
      "product_id": 42
    }
  ]
}
```

### Changed Endpoint

#### My Referral Info
```
GET /api/referral
```

`reward_info` now returns the active reward template info instead of static settings:

```json
{
  "referral_code": "A3F2B1C0",
  "referral_link": "https://yourapp.com?ref=A3F2B1C0",
  "total_referrals": 3,
  "total_rewards": "30000.00",
  "reward_info": {
    "type": "free_delivery",
    "name": "2 free deliveries"
  }
}
```

If no reward is active, `reward_info` will be `null`.

### How Rewards Are Consumed (Automatic)

| Reward | When consumed | What happens |
|---|---|---|
| **Coupon** | User enters coupon code at checkout | Works like any coupon (existing flow) |
| **Free delivery** | Automatically at `POST /api/orders/place` | `delivery_fee` is set to `0`, counter decremented |
| **Bonus product** | Automatically at `POST /api/orders/place` | Product added as free item (`unit_price: 0`) in order items |

Free delivery and bonus product are applied **automatically** — no user action needed. The order response will reflect `delivery_fee: "0"` or show the bonus item with price 0.

### What the Customer App Should Do

1. **Referral page** — Show referral code, share link, and what reward the friend will unlock (from `reward_info`).
2. **Rewards section** — Call `GET /api/rewards` and show active rewards:
   - Coupon: show the code with a "Copy" button, mention it can be used at checkout
   - Free delivery: show "You have N free delivery order(s) remaining"
   - Bonus product: show "Free {product_name} on your next order"
3. **Checkout page** — After placing an order, if free delivery was used, the response will show `delivery_fee: "0"`. If a bonus product was added, it will appear in order items with `unit_price: "0"`. Display these visually (e.g., "Free delivery applied", strikethrough on delivery fee, "Bonus item" badge).
4. **Referral deep link** — On app load, check URL for `?ref=CODE` query param. If present:
   - Store in localStorage
   - After login/register, call `POST /api/referral/apply` with `{"referral_code": "CODE"}`

---

## Flow Summary

```
1. Admin creates reward templates (e.g. "10% coupon", "2 free deliveries", "Free apples")
2. Admin activates one
3. User A shares referral link → User B opens it
4. User B registers and applies referral code
5. User B places and completes their first order
6. Backend automatically grants the active reward to User A
7. User A sees reward in GET /api/rewards
8. User A places an order:
   - Coupon: enters code at checkout
   - Free delivery: auto-applied, delivery_fee = 0
   - Bonus product: auto-added as free item
```
