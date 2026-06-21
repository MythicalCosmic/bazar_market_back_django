# Market Courier App — Backend API Guide

This is the live API for the **Market courier mobile app**. It replaces the
`src/data.js` mock data. Build a small API client (e.g. `src/api.js`) that calls
these endpoints and feeds the shapes into the screens — they match what the UI
already consumes.

---

## 0. Connection basics

| | |
|---|---|
| **Base URL** | `https://api.bazarmarket.org/courier-api` |
| **Content-Type** | `application/json` |
| **Auth** | `Authorization: Bearer <accessToken>` on **every** request except `POST /auth/login` |
| **Currency** | integer UZS so'm, no decimals (e.g. `84600000` = 84 600 000 so'm) |
| **Time zone** | Asia/Tashkent. `placedAt` is `"HH:MM"`; history `date` is ISO. |

### Response envelope ⚠️ IMPORTANT
**Every** response is wrapped in a standard envelope. Your `data` is **inside `data`**:

```json
{ "success": true, "data": { ...the shapes below... }, "responseMS": 42.6 }
```
On error:
```json
{ "success": false, "message": "invalid_credentials", "responseMS": 33.8 }
```
So in your client, **unwrap `response.data`** on success, and read `response.message`
on failure. (`responseMS` is server timing — ignore it.)

### Error status codes
| Code | Meaning |
|---|---|
| `401` | missing/expired/invalid token, or wrong login (`message:"invalid_credentials"`) |
| `403` | token is valid but the account is not a courier (`"Not a courier account"`) |
| `404` | order/resource not found |
| `422` | validation (missing/invalid field) |
| `429` | rate limited (login is throttled) |

---

## 1. Auth

Courier accounts log in with **username + password** (created by an admin — there
is no self-signup). Only accounts with the **courier** role can log in here.

### `POST /auth/login`
Request:
```json
{ "username": "izzatilloxon", "password": "secret" }
```
Response `data`:
```json
{
  "accessToken": "5f3c…(opaque token)",
  "refreshToken": "5f3c…",
  "expiresIn": 259200,
  "courier": {
    "id": "MK-0040",
    "name": "Izzatilloxon",
    "phone": "998910070058",
    "rating": 5.0,
    "vehicle": { "type": "motorcycle", "plate": "" },
    "online": false
  }
}
```
- `401 {message:"invalid_credentials"}` on wrong username/password (show `loginError`).
- Store `accessToken` and send it as `Authorization: Bearer <accessToken>` on all calls.

> Token model: `accessToken` and `refreshToken` are the same opaque token (a server
> session, ~72 h). When a call returns `401`, call `/auth/refresh` to get a fresh
> token. Refresh **rotates** the token — the old one stops working, so always save
> the new pair.

### `POST /auth/refresh`
```json
{ "refreshToken": "5f3c…" }
```
→ same block as login (`accessToken`, `refreshToken`, `expiresIn`, `courier`).

### `POST /auth/logout`
Send the token as `Authorization: Bearer <accessToken>` (no body needed). Invalidates
the session. → `{ "success": true, "message": "Logout successful" }`.

---

## 2. Profile & presence

### `GET /me`
```json
{
  "id": "MK-0040",
  "name": "Izzatilloxon",
  "phone": "998910070058",
  "rating": 5.0,
  "vehicle": { "type": "motorcycle", "plate": "" },
  "online": false,
  "prefs": { "push": true, "sound": true, "accent": "indigo", "lang": "uz", "dark": true }
}
```

### `PATCH /me/online`
Body `{ "online": false }` → `data: { "online": false }`. (The Dashboard pill / Settings toggle.)

### `PATCH /me/prefs`
Body is any subset of `{ push, sound, accent, lang, dark }` (e.g. `{ "accent": "emerald" }`).
Returns the full prefs object. `lang` ∈ `uz | ru` is also saved on the account.

---

## 3. Dashboard

### `GET /dashboard/stats`  (optional `?date=today`)
```json
{
  "ordersToday": 24,
  "delivered": 18,
  "remaining": 6,
  "ordersValue": 84600000,
  "deliveryEarnings": 312000,
  "commission": 846000,
  "totalEarned": 1158000
}
```
- `ordersToday` = orders assigned to you today; `delivered`/`remaining` from those.
- `ordersValue` / `deliveryEarnings` are summed over **today's delivered** orders.
- `commission` = 1 % of `ordersValue`. `totalEarned` = `commission + deliveryEarnings`.

---

## 4. Active orders

### `GET /orders/active`
```json
{
  "orders": [
    {
      "id": "ORD-20260607-94F9A6",
      "customer": "Abrorbek Qodirjonov",
      "phone": "998990358849",
      "address": "Andijon, Marhamat, Beruniy ko‘chasi 259",
      "district": "Uy",
      "distanceKm": null,
      "etaMin": null,
      "payment": "card",
      "status": "new",
      "deliveryFee": 10000,
      "placedAt": "19:18",
      "origin": null,
      "dest": { "lat": 40.4959637, "lng": 72.3224888 },
      "items": [ { "name": "Biscona Chocolate", "qty": 1, "price": 24000 } ]
    }
  ]
}
```
- `status` ∈ `new | accepted | picked | onway | delivered` (the courier flow).
- `payment` ∈ `cash | card`.
- `dest` = real delivery `lat/lng` (use for the map & the "Navigate" deep link).
- `origin` / `distanceKm` / `etaMin` are **`null` for now** — the server has no store
  coordinates / routing engine configured yet. If you need distance, compute it
  client-side from `dest`, or we can enable it server-side (see Notes).
- `district` is best-effort (the address label, e.g. "Uy"); there is no dedicated
  district field in the data.

### `GET /orders/{id}`
`{id}` is the `id` from the list (the order number, e.g. `ORD-20260607-94F9A6`).
Returns a single order with the **same shape** as a list item.

### `PATCH /orders/{id}/status`
Advance the order one legal step (`new → accepted → picked → onway → delivered`):
```json
{ "status": "picked" }
```
Response `data`:
```json
{ "id": "ORD-20260607-94F9A6", "status": "picked", "updatedAt": "2026-06-21T13:05:00Z" }
```
- The server validates it is the **next** legal step (else `422`).
- Reaching `onway`/`delivered` also moves the order forward in the main system
  (so the customer/admin see it). `delivered` is terminal.
- Convenience: `POST /orders/{id}/advance` (no body) bumps to the next status automatically.

---

## 5. Order history

### `GET /orders/history`
Query params: `period=today|week|month` · `status=all|delivered|cancelled` ·
`q=<search customer/order#>` · `page=1` · `pageSize=20`.

```json
{
  "summary": { "earned": 31700, "deliveredCount": 4, "totalCount": 6 },
  "page": 1,
  "pageSize": 20,
  "total": 6,
  "orders": [
    {
      "id": "ORD-20260607-331DFF",
      "customer": "Tohirbek",
      "district": "Uy",
      "status": "delivered",
      "total": 20000,
      "deliveryFee": 10000,
      "items": 1,
      "date": "2026-06-07T14:31:40Z",
      "earned": 10200
    }
  ]
}
```
- `status` ∈ `delivered | cancelled`. `earned` = `deliveryFee + 1% of total`
  (and `0` for cancelled). `summary.earned` is the period total for the gradient card.
- `date` is ISO — format it in the app.

---

## 6. Push notifications (device registration)

### `POST /devices`
```json
{ "token": "ExponentPushToken[xxxx]", "platform": "android" }
```
→ `{ "success": true, "message": "Device registered" }`. Call after login.

### `DELETE /devices/{token}`
Unregister on logout / when Push is turned off. The token may also be sent in the
request body (`{ "token": "..." }`) — preferred if it contains `/` or `+`.

> Note: device tokens are stored, but the server does **not** yet *send* pushes on
> new-order assignment (that wiring is a later step). For now, poll for new work.

---

## 7. Real-time / navigation

- **No WebSocket yet.** For live updates, poll `GET /orders/active` and
  `GET /dashboard/stats` every ~30 s (or on screen focus / pull-to-refresh).
- **Navigate button:** build the maps deep link from the order's `dest.lat/lng`
  (Yandex / Google / 2GIS) — no backend call needed.

---

## Endpoint summary

| Action | Method & path |
|---|---|
| Login | `POST /auth/login` |
| Refresh token | `POST /auth/refresh` |
| Logout | `POST /auth/logout` |
| Profile | `GET /me` |
| Online toggle | `PATCH /me/online` |
| Save prefs | `PATCH /me/prefs` |
| Dashboard stats | `GET /dashboard/stats` |
| Active orders | `GET /orders/active` |
| Order detail | `GET /orders/{id}` |
| Advance status | `PATCH /orders/{id}/status` (or `POST /orders/{id}/advance`) |
| History | `GET /orders/history` |
| Register device | `POST /devices` |
| Unregister device | `DELETE /devices/{token}` |

*All paths are relative to `https://api.bazarmarket.org/courier-api`. All `PATCH`
endpoints also accept `POST` if your HTTP client can't send `PATCH`.*
