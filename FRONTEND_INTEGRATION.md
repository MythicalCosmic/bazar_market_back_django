# Bazar Market — Client Frontend Page Spec

End-to-end page-by-page spec for the customer frontend, aligned to the current API.

---

## Conventions & global state

**Languages**: `uz`, `ru`. App-wide language switch persisted both in localStorage and on the user (`language` field). Every product/category text has `_uz` and `_ru` variants — always render based on `lang`.

**Auth**:
- Bearer token in `Authorization: Bearer <session_key>`
- Persist `session_key` + `expires_at` in secure storage (Keychain / Keystore / `localStorage` + `Secure-` cookie)
- 401 → wipe session + push to Login
- 720h session lifetime (30 days)

**API base**: `/api/` for customer endpoints. All POST bodies are JSON. Common envelope:
```json
{"success": true, "data": {...}, "message": "..."}
{"success": false, "message": "...", "errors": [...]}
```

**Currency**: UZS. Format with thousands separators, no decimals (`12,000 so'm`).

**Phone format**: `+998XXXXXXXXX`. Validate client-side before sending; the server stores raw.

**Empty states / skeletons**: every list page must render skeletons during fetch and a friendly empty state when the list is empty. No silent blank screens.

**Error toasts**: parse `data.message`; for validation, surface field-level `data.errors` if present.

**Network**: retry idempotent GETs once on transient failure; never retry POSTs without idempotency tokens.

---

# 1. App entry & onboarding

## 1.1 Splash / Bootstrap
**Route**: `/` on cold start.
**Purpose**: Determine where to send the user.
**Logic**:
1. Read stored session_key.
2. If present and not expired → call `GET /api/auth/me`. On 200 → home. On 401 → wipe and go to language pick or login.
3. If no language picked yet → Onboarding/Language.
4. If language picked but no session → Login.

No UI beyond a logo + spinner. Timeout: 5s, then show "Connection problem — retry".

## 1.2 Language picker (first launch)
**Route**: `/onboarding/language`
**Purpose**: First-time language selection.
**Sections**:
- Logo
- Two large buttons: "🇺🇿 O'zbekcha", "🇷🇺 Русский"
- "Continue" disabled until picked

**On confirm**: store in localStorage as `lang`, push to `/auth/login`.
**Note**: This page is *not* shown to returning users. Language can later be changed from Profile.

---

# 2. Authentication

All auth screens share a layout: logo top, form center, terms link bottom ("By continuing you agree to terms").

## 2.1 Login (phone entry)
**Route**: `/auth/login`
**Purpose**: Existing user enters phone → server sends SMS.
**Form**:
- Phone (mask `+998 (__) ___ __ __`, validates `+998XXXXXXXXX` 13 chars)
- "Send code" button
- "Don't have an account? Register" link below

**Submit**: `POST /api/auth/login` `{phone}`
**Response**: always `200` with `{"message": "If an account exists for this phone, a verification code has been sent", "expires_in": 120}` — **do not** branch on whether the account exists. (This is enumeration-safe by design.)
**Navigate**: always to `/auth/login/verify?phone=...` regardless of response. If user typed an unregistered phone they'll fail at the next step.
**Errors**:
- `422` "phone is required" → inline field error
- `429` rate-limited → "Too many requests, try again in N seconds" using `Retry-After`
- network → toast "No connection"

## 2.2 Login OTP verification
**Route**: `/auth/login/verify?phone=...`
**Form**:
- 6 separated digit boxes (auto-advance, paste-friendly)
- Resend countdown (60s) — disabled until 0
- "Use a different phone" link → back to `/auth/login`

**Submit**: `POST /api/auth/login/verify` `{phone, code, device}`
**Success**: store `session_key` + `expires_at` + serialized user; push to `/home`.
**Errors**:
- `400` "Invalid or expired verification code" → inline below boxes; clear input
- `400` "No pending login..." → push back to `/auth/login`
- After 5 wrong attempts the OTP self-invalidates server-side; user gets the same message, must Resend.

**Resend**: `POST /api/auth/login/resend` `{phone}` — restart 60s countdown. Rate-limited 1/min.

## 2.3 Register (sign up)
**Route**: `/auth/register`
**Purpose**: New user. Phone + name only. No password.
**Form**:
- First name (required)
- Last name (optional)
- Phone (validated)
- Language picker (optional, defaults to current app lang)
- "Have a referral code?" expandable → text input (optional, applied after first order, not at registration)
- "Send verification code" button
- "Already have an account? Login" link

**Submit**: `POST /api/auth/register` `{phone, first_name, last_name?, language?}`
**On success**: navigate to `/auth/register/verify?phone=...`.
**Errors**:
- `400` "Phone number already registered" → inline "Already a member? Log in"
- `400` "Telegram account already registered" → only relevant if you wire telegram_id from a Telegram WebApp launch
- `422` missing fields

Hold the referral code in app state until registration completes; apply via `POST /api/referral/apply` after first session created.

## 2.4 Register OTP verification
**Route**: `/auth/register/verify?phone=...`
**Same UX as login verify.**
**Submit**: `POST /api/auth/register/verify` `{phone, code, device}`
**Success**: returns `session_key` and `user`. Persist, push to `/home`. If a referral code was held, immediately call `POST /api/referral/apply` `{code}` (don't block UX on it; show toast on success).
**Errors**: same patterns.
**Resend**: `POST /api/auth/register/resend`.

## 2.5 Pending registration expired
If user returns 2+ minutes after register and tries `verify`, server replies `"Registration expired"`. Push to `/auth/register` with phone pre-filled.

---

# 3. Home & catalog

## 3.1 Home
**Route**: `/home`
**Purpose**: Landing after login. Promotional + entry points to catalog.
**Sections** (top to bottom):
1. **Top bar**: app logo, location chip ("Deliver to: Home" with arrow → opens address picker sheet), bell icon (notifications, badge from `GET /api/notifications/unread-count`), language flag toggle.
2. **Search bar** (sticky). Tapping → `/search`.
3. **Banners carousel** (`GET /api/banners`). Swipeable; tap opens deep link from banner payload (category, product, or external URL).
4. **Categories grid** (`GET /api/categories/tree`) — horizontally scrollable chips OR 4-column grid of root categories with images.
5. **Featured products** (`GET /api/products/featured`) — horizontal carousel; "See all" → `/products?is_featured=1`.
6. **Popular products** (`GET /api/products/popular`) — horizontal carousel; "See all" → `/products?order_by=popular`.
7. **Active discounts** (optional section: filter products with `_discounted_price`).
8. **Bottom nav**: Home / Categories / Cart (badge) / Orders / Profile.

**Pull-to-refresh**: refetches all sections in parallel.
**Loading**: skeleton cards.
**Empty banners**: hide section silently.

## 3.2 Categories list (flat)
**Route**: `/categories`
**Endpoint**: `GET /api/categories`
**Layout**: Vertical list with image + name + product count.
**Tap**: → `/products?category_id=<id>` showing products in that category.

## 3.3 Category tree
**Route**: `/categories/tree` (or as a side drawer)
**Endpoint**: `GET /api/categories/tree`
**Layout**: roots with expandable subcategories. Tapping a leaf → product list filtered.

## 3.4 Product list (catalog)
**Route**: `/products?category_id=...&q=...&is_featured=...&order_by=...&page=...`
**Endpoint**: `GET /api/products`
**Sections**:
- **Header**: category name (if filtered), result count, sort dropdown (Default / Price ↑ / Price ↓ / Newest / Popular).
- **Filter bar**: chips for active filters; tap to remove. "Filters" button opens sheet (price range, in-stock toggle, has-discount toggle).
- **Grid**: 2-column product cards
  - Primary image
  - Name (per lang)
  - Price (strikethrough original if `discounted_price` present + new price in red)
  - "❤" favorite toggle button (state from preloaded favorites set)
  - "Add" button → `POST /api/cart/add`
- **Pagination**: infinite scroll or page numbers.

**Empty**: "No products in this category"
**Each card tap**: → `/product/<id>`

## 3.5 Product detail
**Route**: `/product/<id>`
**Endpoint**: `GET /api/product/<id>`
**Sections**:
- **Image gallery** (swipe between `images[]`).
- **Title** (per lang) + favorite toggle.
- **Price block**: original / discounted; "🏷 Discount: -20%" badge if `_current_discounts`.
- **Stock**: "In stock" / "Only N left" / "Out of stock" badge.
- **Quantity stepper**: respects `min_qty`, `max_qty`, `step`. Disable + when at max or stock limit.
- **Description** (per lang) — collapsible.
- **Specs**: unit (kg/piece/etc), barcode, sku — small grid.
- **Reviews summary**: avg star + count + "See all" → `/product/<id>/reviews` (read-only listing — no public endpoint defined yet, surface reviews tied to your own past orders only via the existing `GET /api/reviews`).
- **Related/popular** (optional carousel of `/api/products/popular`).
- **Sticky footer**: "Add to cart" button — full width. Disabled if out of stock.

**Action**: `POST /api/cart/add` `{product_id, quantity}` → toast "Added", update cart badge.
**Out of stock**: button replaced with "Notify me" (if you build it; otherwise just disable).

## 3.6 Search
**Route**: `/search`
**Endpoint**: `GET /api/products/search?query=...`
**Layout**:
- Search input with autofocus, clear button.
- Recent searches (local) below until typing.
- Live results after debounce (300ms, min 2 chars).
- Same product card grid as 3.4.

**Empty**: "No results for X"

---

# 4. Cart & checkout

## 4.1 Cart
**Route**: `/cart`
**Endpoint**: `GET /api/cart`
**Layout**:
- **Empty state**: illustration + "Your cart is empty" + "Browse products" CTA → home.
- **Populated**:
  - List of cart items: image, name, unit price (with `discounted_price` if present), qty stepper, line total, ✕ remove.
  - Stepper updates: `POST /api/cart/update` `{product_id, quantity}` (sets quantity; passing 0 removes).
  - Remove: `POST /api/cart/remove` `{product_id}`.
  - "Clear cart" link → `POST /api/cart/clear` (with confirm dialog).
  - **Coupon row**: text input + "Apply" → `POST /api/coupon/validate` (client passes server-computed subtotal — but **never trust the response value** for charging; it's preview only, server re-validates at place_order).
  - **Summary card**: subtotal, delivery fee (placeholder until address picked), discount, total.
  - **CTA**: "Checkout" button → `/checkout`.
- **Stale items**: if backend says `in_stock=false` or `stock_qty < quantity`, mark the line in red + "out of stock" badge; checkout disabled until resolved.
- **Price drift warning**: if a line shows `discounted_price` but on revisit it changed, show a small "Price updated" indicator (optional).

## 4.2 Checkout
**Route**: `/checkout`
**Sections**:
1. **Delivery address** picker
   - Loads user's `GET /api/addresses`, default selected.
   - Tap → opens address sheet with list + "Add new" CTA.
   - "Check delivery": calls `POST /api/delivery/check` `{lat, lng}` to confirm zone covers and show fee/min/eta. Block continue if no zone.
2. **Payment method**: radio
   - Cash on delivery
   - Card (cash/card per `VALID_PAYMENT_METHODS`)
3. **Coupon** (chip showing applied coupon, with ✕ to remove)
4. **Scheduled delivery** (optional toggle): date/time picker; min = now + 1h. Sends as ISO `scheduled_time`.
5. **Note to courier** (optional textarea, max 500 chars)
6. **Order summary** (subtotal, delivery, discount, **rewards** if any will apply, total)
7. **Sticky footer**: "Place order" button.

**Submit**: `POST /api/orders/place`
```json
{
  "address_id": 12,
  "payment_method": "cash",
  "coupon_code": "SUMMER10",
  "scheduled_time": "2026-05-07T15:00:00",
  "user_note": "Gate code 4321"
}
```
**On success** → `/order/<order_id>?placed=1` (confirmation page).
**Errors to handle**:
- `400` "Cart is empty" → push to `/cart`
- `400` "Address not found" / "Invalid payment method" → inline
- `400` `errors:[...]` "Some products are unavailable" → mark items red, push back to `/cart`
- `400` "Minimum order total is X"
- `400` "This coupon..." → clear coupon, surface message
- `400` "scheduled_time cannot be in the past"
- network/timeout → idempotency note: place_order is **not** idempotent server-side; lock the button after first tap to prevent double submit.

## 4.3 Order placed (confirmation)
**Route**: `/order/<id>?placed=1`
**Layout**:
- ✅ "Order #ORD-20260506-XXXXXX placed"
- ETA from delivery zone
- Summary card with items, totals
- "Track order" button → same page without `?placed=1` (reloads as detail)
- "Continue shopping" → home

---

# 5. Orders

## 5.1 Orders list
**Route**: `/orders`
**Tabs**: **Active** / **History**
- Active: `GET /api/orders/active`
- History: `GET /api/orders?status=completed&page=...` (or all paged)

**Card per order**:
- Order # + status badge (color-coded)
- Date
- N items + total
- "View" → detail

**Pull-to-refresh** updates active tab.
**Empty Active**: "No active orders. [Browse products]"
**Empty History**: "You haven't placed any orders yet"

## 5.2 Order detail
**Route**: `/order/<id>`
**Endpoint**: `GET /api/order/<id>` (returns order + items + status_log inlined)
**Sections**:
1. **Status tracker**: horizontal stepper Pending → Confirmed → Preparing → Delivering → Delivered → Completed. Cancelled is a side branch with its own indicator.
2. **Order # + date + payment status badge**.
3. **Items list** (snapshot from order — `product_name`, `unit_price`, `quantity`, `total`).
4. **Delivery card**: address, courier name + phone (when assigned, post-`preparing` status), scheduled_time if any.
5. **Totals**: subtotal, delivery, discount, total.
6. **Note to courier** (read-only).
7. **Footer actions**:
   - If `status == pending`: ✕ "Cancel order" → confirm dialog → `POST /api/order/<id>/cancel` `{reason}`.
   - If `status in [delivered, completed]`: 🔁 "Reorder" → `POST /api/order/<id>/reorder` (adds items back to cart, navigate to `/cart`).
   - If `status == delivered` and not yet reviewed: ⭐ "Leave a review" → `/review/submit?order_id=<id>`.

**Auto-refresh**: poll every 30s while tab is open, only for active statuses; or use SSE/websocket if you wire one. For now, polling is acceptable.

## 5.3 Cancel order modal
**Trigger**: from order detail (only when `status == pending`).
**Form**: optional reason (textarea), "Confirm cancel" + "Keep order" buttons.
**Submit**: `POST /api/order/<id>/cancel`. Rate-limited 10/min.
**On success**: refresh order detail; toast "Order cancelled". Stock will be restored, coupon usage rolled back server-side — no client work.

## 5.4 Reorder
**Trigger**: from history.
**Endpoint**: `POST /api/order/<id>/reorder`
**Behavior**: adds available items to cart; returns `added` and `skipped` lists. Show a sheet listing skipped items with reasons ("out of stock"), then push to `/cart`.

---

# 6. Addresses

## 6.1 Addresses list
**Route**: `/addresses`
**Endpoint**: `GET /api/addresses`
**Layout**: list of cards with label (Home/Work), text, default star.
**Actions** per card: Edit, Delete, Set default.
**FAB**: "+ Add address" → `/address/add`.
**Empty**: "Save your delivery addresses for faster checkout"

## 6.2 Add / edit address
**Route**: `/address/add` and `/address/<id>/update`
**Form**:
- **Map** (Yandex / Google) with draggable pin, search box for street.
- Read lat/lng from pin position.
- "Use my current location" button.
- Label (Home / Work / Custom)
- Address text (autofilled from reverse geocode, editable)
- Entrance, floor, apartment (optional, short text)
- Comment (textarea)
- "Set as default" checkbox

**On submit**:
- Add: `POST /api/address/add`
- Update: `PATCH /api/address/<id>/update` (note: this endpoint is PATCH, not POST — verify in HTTP client)

**Validate**: lat/lng numeric, address_text non-empty.
**Delete** (edit mode only): `POST /api/address/<id>/delete` with confirm.
**Set default**: `POST /api/address/<id>/default`.

## 6.3 Delivery zone check
Used inline at checkout (4.2). Standalone "Where do you deliver?" page:
**Route**: `/delivery/info`
**Endpoint**: `GET /api/delivery/info`
**Layout**: map showing all zones as polygons + per-zone min order / fee / ETA list.

---

# 7. Favorites & reviews

## 7.1 Favorites
**Route**: `/favorites`
**Endpoint**: `GET /api/favorites`
**Layout**: same product card grid as catalog. Heart on each card is filled.
**Toggle**: `POST /api/favorite/<product_id>/toggle` — optimistic update, rollback on failure.
**Empty**: "Save items you love" + heart illustration.

## 7.2 My reviews
**Route**: `/reviews`
**Endpoint**: `GET /api/reviews`
**Layout**: list of past reviews with rating stars, comment, order link.
**Empty**: "Reviews you submit appear here"

## 7.3 Submit review
**Route**: `/review/submit?order_id=<id>` (modal/sheet preferred)
**Form**:
- Star rating (1–5, required)
- Comment (textarea, optional, max 1000 chars)

**Submit**: `POST /api/review/submit` `{order_id, rating, comment}`
**Errors**: `400` "You have already reviewed this order" → close modal; or "This order is not eligible for review" (must be delivered).
**On success**: toast "Thanks for your feedback!" + return to order detail.

---

# 8. Notifications

## 8.1 Notifications list
**Route**: `/notifications`
**Endpoint**: `GET /api/notifications?page=...&per_page=...` (server already paginates; pass `?page=`)
**Layout**:
- "Mark all read" link top right (`POST /api/notifications/read-all`)
- List items: icon by `type`, title, body, time-ago, unread dot.
- Tap: marks read (`POST /api/notification/<id>/read`) + handles `payload` deep link (e.g. `{order_id: 123}` → `/order/123`).

**Pull-to-refresh** + infinite scroll.
**Empty**: "You're all caught up"

## 8.2 Unread badge
- Polled at app foreground / every 60s while app open: `GET /api/notifications/unread-count`.
- Or pushed via Telegram bot for users who linked.

---

# 9. Account / Profile

## 9.1 Profile (account home)
**Route**: `/profile`
**Endpoint**: `GET /api/auth/me`
**Sections**:
- **Header**: avatar (initials), name, phone, "Edit" → `/profile/edit`.
- **Menu rows** (each → its own page):
  - 📦 My orders → `/orders`
  - 📍 Addresses → `/addresses`
  - ❤️ Favorites → `/favorites`
  - ⭐ My reviews → `/reviews`
  - 🎁 Referrals → `/referrals`
  - 🏆 Rewards → `/rewards`
  - 🔔 Notifications → `/notifications`
  - 🌐 Language → modal toggle (uz/ru) → `PATCH /api/auth/me/update` `{language}`
  - ⚙️ Settings → `/settings`
  - ❓ Help / FAQ → static page
- **Footer**: app version + build.

## 9.2 Edit profile
**Route**: `/profile/edit`
**Form**:
- First name, last name, language
- **Phone is read-only here**, with a "Change" button → `/profile/phone`

**Submit**: `PATCH /api/auth/me/update` `{first_name, last_name, language}`. Phone is not accepted by this endpoint — separate flow.

## 9.3 Change phone — request
**Route**: `/profile/phone`
**Form**:
- Current phone (read-only, prefilled)
- New phone (validated)
- "Send code to new phone" button

**Submit**: `POST /api/auth/me/phone` `{new_phone}`
**On success** → `/profile/phone/verify`.
**Errors**:
- "New phone is the same as current"
- "Phone number already in use"
- `429` rate-limited (3/min)

## 9.4 Change phone — verify
**Route**: `/profile/phone/verify`
**Form**: 6-digit code input + resend countdown.
**Submit**: `POST /api/auth/me/phone/verify` `{code}`
**On success**: server invalidates **all** existing sessions (including this one). Show "Phone updated. Please log in again." → wipe session → `/auth/login` with new phone prefilled.

## 9.5 Settings
**Route**: `/settings`
**Sections**:
- **Account**:
  - Logout → `POST /api/auth/logout` → wipe + `/auth/login`
  - Logout from all devices → `POST /api/auth/logout-all` (with confirm)
  - Delete account → confirm modal → `POST /api/auth/me/delete` (irreversible warning) → wipe + onboarding.
- **Notifications** (toggle preferences, if you have a settings model — currently not API-backed; UI placeholder).
- **Legal**: Terms of Service, Privacy (static).
- **About**: version, build, support contact.

---

# 10. Referrals & rewards

## 10.1 Referrals
**Route**: `/referrals`
**Endpoints**:
- `GET /api/referral` — my code, link, stats (count, rewards_total)
- `GET /api/referral/list` — list of users I referred + their first-order status

**Sections**:
- **Card**: "Invite a friend, earn rewards"
- Code in monospace + "Copy" + "Share" (system share sheet with `link`)
- Stats: invited count, rewards earned
- **Apply someone else's code** — text input + "Apply" → `POST /api/referral/apply` `{code}`
  - One-time only; on success show "Code applied! You'll get a reward after your first order." Hide input afterwards.
  - Errors: "Invalid code", "Already applied", "Cannot refer yourself"
- **Recent referrals** list: name, joined date, "first order placed" badge.

## 10.2 Rewards
**Route**: `/rewards`
**Endpoint**: `GET /api/rewards`
**Layout**: list of active rewards
- "Free delivery × N" cards (with remaining count)
- "Bonus product" cards (product image, "Add to next order" — applied automatically server-side at place_order)

**Empty**: "Place orders to earn rewards"

---

# 11. Coupons (UX placement)

There is no dedicated coupons list endpoint for customers (admin-curated). Coupons enter the app via:
- Banner CTA (banner payload may carry `coupon_code` to copy)
- Manual entry at checkout
- Push from referral reward

When a referral coupon is granted, store it in app state as a chip "You have a SUMMER10 coupon" displayed on cart and home until used.

---

# 12. Banners (deep-linked content)

`GET /api/banners` returns title + image + payload. Banner payload can be:
- `{type: "category", category_id: 12}` → push `/products?category_id=12`
- `{type: "product", product_id: 99}` → push `/product/99`
- `{type: "url", url: "https://..."}` → open in webview
- `{type: "coupon", code: "SUMMER10"}` → copy + show toast + push `/cart`

Define this contract on your end and document it in the admin DTO.

---

# 13. Telegram WebApp launch (optional)

If app runs inside Telegram WebApp:
- Read `Telegram.WebApp.initDataUnsafe.user.id` → pass as `telegram_id` during register.
- Skip language picker (use `Telegram.WebApp.initDataUnsafe.user.language_code` if `uz`/`ru`).
- Use `Telegram.WebApp.MainButton` instead of in-page CTAs on Cart/Checkout.

---

# 14. Errors & system pages

## 14.1 No internet
Full-screen banner with offline icon + "Retry" button. Trigger when fetch fails with no response. Persistent connectivity listener; auto-retries.

## 14.2 Maintenance / 503
If any API returns 503, show full-screen "We'll be right back" page with retry-after countdown.

## 14.3 Forced logout (401 from any endpoint)
Wipe session, push to `/auth/login`, show toast "Session expired, please log in again".

## 14.4 Rate limited (429)
Show inline error with countdown from `Retry-After` header. Disable submit until 0.

## 14.5 Generic error / 500
Toast with `data.message` if present, else "Something went wrong". Don't auto-retry POSTs.

## 14.6 Unsupported app version
If you add an `app_version` enforcement endpoint later, check on splash and force-update screen with store link.

---

# 15. Page-by-page state checklist

For every list page apply: **idle → fetching (skeletons) → empty → populated → error → refreshing**.
For every form: **idle → invalid (per-field errors) → submitting (button spinner) → success → server error**.
For every detail page: **idle → fetching → not-found (404) → populated → action-pending → action-success → action-error**.

---

# 16. Endpoint → Page index

| Endpoint | Pages |
|---|---|
| `POST /api/auth/register` | 2.3 |
| `POST /api/auth/register/verify` | 2.4 |
| `POST /api/auth/register/resend` | 2.4 |
| `POST /api/auth/login` | 2.1 |
| `POST /api/auth/login/verify` | 2.2 |
| `POST /api/auth/login/resend` | 2.2 |
| `POST /api/auth/logout` | 9.5 |
| `POST /api/auth/logout-all` | 9.5 |
| `GET /api/auth/me` | 1.1, 9.1 |
| `PATCH /api/auth/me/update` | 9.2, 9.1 (lang switch) |
| `POST /api/auth/me/phone` | 9.3 |
| `POST /api/auth/me/phone/verify` | 9.4 |
| `POST /api/auth/me/delete` | 9.5 |
| `GET /api/products` | 3.4 |
| `GET /api/products/featured` | 3.1 |
| `GET /api/products/popular` | 3.1 |
| `GET /api/products/search` | 3.6 |
| `GET /api/product/<id>` | 3.5 |
| `GET /api/categories` | 3.2 |
| `GET /api/categories/tree` | 3.1, 3.3 |
| `GET /api/cart` | 4.1 |
| `POST /api/cart/add` | 3.4, 3.5 |
| `POST /api/cart/update` | 4.1 |
| `POST /api/cart/remove` | 4.1 |
| `POST /api/cart/clear` | 4.1 |
| `GET /api/addresses` | 6.1, 4.2 |
| `POST /api/address/add` | 6.2 |
| `PATCH /api/address/<id>/update` | 6.2 |
| `POST /api/address/<id>/delete` | 6.2 |
| `POST /api/address/<id>/default` | 6.2 |
| `GET /api/orders` | 5.1 |
| `GET /api/orders/active` | 5.1 |
| `POST /api/orders/place` | 4.2 |
| `GET /api/order/<id>` | 5.2, 4.3 |
| `POST /api/order/<id>/cancel` | 5.3 |
| `POST /api/order/<id>/reorder` | 5.4 |
| `GET /api/favorites` | 7.1 |
| `POST /api/favorite/<id>/toggle` | 3.4, 3.5, 7.1 |
| `POST /api/favorite/<id>/check` | 3.5 (precheck) |
| `GET /api/reviews` | 7.2 |
| `POST /api/review/submit` | 7.3 |
| `GET /api/notifications` | 8.1 |
| `POST /api/notifications/read-all` | 8.1 |
| `GET /api/notifications/unread-count` | 3.1 (badge), 8.2 |
| `POST /api/notification/<id>/read` | 8.1 |
| `GET /api/referral` | 10.1 |
| `GET /api/referral/list` | 10.1 |
| `POST /api/referral/apply` | 10.1, 2.4 (post-register) |
| `GET /api/rewards` | 10.2 |
| `POST /api/coupon/validate` | 4.1, 4.2 |
| `GET /api/banners` | 3.1, 12 |
| `POST /api/delivery/check` | 4.2, 6.2 |
| `GET /api/delivery/info` | 6.3 |

---

# 17. Bottom-nav layout (mobile reference)

```
[ Home ] [ Catalog ] [ 🛒 Cart (badge) ] [ Orders ] [ Profile ]
```

Top-right persistent: language switcher chip + bell with unread count.
