#!/usr/bin/env python
"""Comprehensive endpoint tester — hits every route with valid, invalid, and edge-case payloads."""
import json
import time
import requests

BASE = "http://localhost:9999"
RESULTS = []
ADMIN_TOKEN = None
CUSTOMER_TOKEN = None
CREATED_IDS = {}


def req(method, path, body=None, token=None, label="", expect=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    start = time.time()
    try:
        r = getattr(requests, method)(url, json=body, headers=headers, timeout=15)
        elapsed = round((time.time() - start) * 1000, 1)
    except Exception as e:
        RESULTS.append({"path": path, "method": method.upper(), "status": "ERR", "label": label, "detail": str(e)})
        return None

    try:
        data = r.json()
    except Exception:
        data = {}

    status_ok = True
    if expect and r.status_code != expect:
        status_ok = False

    detail = ""
    if not data.get("success", True) and r.status_code < 400:
        detail = data.get("message", "")
    elif r.status_code >= 500:
        detail = f"SERVER ERROR: {r.text[:200]}"
        status_ok = False

    RESULTS.append({
        "path": path,
        "method": method.upper(),
        "status": r.status_code,
        "ms": elapsed,
        "label": label,
        "ok": status_ok,
        "detail": detail,
    })
    return data, r.status_code


# ═══════════════════════════════════════════════════
# CUSTOMER API TESTS
# ═══════════════════════════════════════════════════

print("=" * 60)
print("CUSTOMER API TESTS")
print("=" * 60)

# ── Auth ──
# Register with missing fields
req("post", "/api/auth/register", {}, label="register: empty body", expect=422)
req("post", "/api/auth/register", {"phone": "+998991111111"}, label="register: missing fields", expect=422)
req("post", "/api/auth/register", {"phone": "+998991111111", "first_name": "T", "password": "12"}, label="register: short password", expect=422)

# Register valid test user
r = req("post", "/api/auth/register", {
    "phone": "+998999999999",
    "first_name": "TestUser",
    "password": "test123456",
    "language": "uz",
}, label="register: valid", expect=201)
if r and r[1] == 201:
    CUSTOMER_TOKEN = r[0]["data"]["session_key"]
elif r and r[1] == 422:
    # User may already exist, try login
    r2 = req("post", "/api/auth/login", {"phone": "+998999999999", "password": "test123456"}, label="login: existing test user")
    if r2 and r2[1] == 200:
        CUSTOMER_TOKEN = r2[0]["data"]["session_key"]

# Login tests
req("post", "/api/auth/login", {}, label="login: empty body", expect=422)
req("post", "/api/auth/login", {"phone": "+998999999999", "password": "wrongpassword"}, label="login: wrong password", expect=401)
req("post", "/api/auth/login", {"phone": "+998000000000", "password": "test"}, label="login: nonexistent phone", expect=401)

# Login valid — try the test user, fall back to existing user
if not CUSTOMER_TOKEN:
    r = req("post", "/api/auth/login", {"phone": "+998999999999", "password": "test123456"}, label="login: valid")
    if r and r[1] == 200:
        CUSTOMER_TOKEN = r[0]["data"]["session_key"]
if not CUSTOMER_TOKEN:
    r = req("post", "/api/auth/login", {"phone": "+998990358849", "password": "test123456"}, label="login: fallback user")
    if r and r[1] == 200:
        CUSTOMER_TOKEN = r[0]["data"]["session_key"]

# Verify phone (will fail without real OTP but should return 422, not 500)
req("post", "/api/auth/verify", {"code": "000000"}, token=CUSTOMER_TOKEN, label="verify: wrong code", expect=422)
req("post", "/api/auth/verify", {}, token=CUSTOMER_TOKEN, label="verify: empty body", expect=422)
req("post", "/api/auth/verify", {"code": "123456"}, label="verify: no auth", expect=401)

# Resend code
req("post", "/api/auth/resend-code", token=CUSTOMER_TOKEN, label="resend-code")

# Me
req("get", "/api/auth/me", token=CUSTOMER_TOKEN, label="me: valid", expect=200)
req("get", "/api/auth/me", label="me: no auth", expect=401)

# Update profile
req("patch", "/api/auth/me/update", {"first_name": "UpdatedName"}, token=CUSTOMER_TOKEN, label="update profile: valid", expect=200)
req("patch", "/api/auth/me/update", {"language": "xx"}, token=CUSTOMER_TOKEN, label="update profile: bad language", expect=422)
req("patch", "/api/auth/me/update", {"password": "ab"}, token=CUSTOMER_TOKEN, label="update profile: short password", expect=422)
req("patch", "/api/auth/me/update", "not json", token=CUSTOMER_TOKEN, label="update profile: invalid json")

# Logout all (will invalidate token, so do last)
# Save for later

# ── Catalog (Public) ──
req("get", "/api/products", label="products: list", expect=200)
req("get", "/api/products?page=1&per_page=5", label="products: paginated", expect=200)
req("get", "/api/products?page=abc", label="products: bad page", expect=422)
req("get", "/api/products?category_id=1", label="products: by category", expect=200)
req("get", "/api/products?category_id=abc", label="products: bad category_id", expect=422)
req("get", "/api/products?q=olma", label="products: search query", expect=200)
req("get", "/api/products?is_featured=true", label="products: featured filter", expect=200)
req("get", "/api/products?order_by=price", label="products: order by price", expect=200)
req("get", "/api/products?order_by=-price", label="products: order by -price", expect=200)
req("get", "/api/products?per_page=999", label="products: per_page > 100 (should cap)", expect=200)

req("get", "/api/product/2", label="product detail: valid", expect=200)
req("get", "/api/product/99999", label="product detail: nonexistent", expect=404)

req("get", "/api/products/featured", label="featured products", expect=200)
req("get", "/api/products/popular", label="popular products", expect=200)
req("get", "/api/products/search?q=suv", label="search: valid", expect=200)
req("get", "/api/products/search", label="search: no query", expect=422)
req("get", "/api/products/search?q=", label="search: empty query", expect=422)

req("get", "/api/categories", label="categories", expect=200)
req("get", "/api/categories/tree", label="category tree", expect=200)

# ── Cart ──
req("get", "/api/cart", token=CUSTOMER_TOKEN, label="cart: get", expect=200)
req("get", "/api/cart", label="cart: no auth", expect=401)
req("post", "/api/cart/add", {"product_id": 2, "quantity": "1"}, token=CUSTOMER_TOKEN, label="cart: add valid", expect=200)
req("post", "/api/cart/add", {"product_id": 99999, "quantity": "1"}, token=CUSTOMER_TOKEN, label="cart: add nonexistent product", expect=404)
req("post", "/api/cart/add", {"product_id": 2, "quantity": "-1"}, token=CUSTOMER_TOKEN, label="cart: add negative qty", expect=422)
req("post", "/api/cart/add", {"product_id": 2, "quantity": "abc"}, token=CUSTOMER_TOKEN, label="cart: add non-numeric qty", expect=422)
req("post", "/api/cart/add", {}, token=CUSTOMER_TOKEN, label="cart: add empty body", expect=422)
req("post", "/api/cart/update", {"product_id": 2, "quantity": "3"}, token=CUSTOMER_TOKEN, label="cart: update qty", expect=200)
req("post", "/api/cart/update", {"product_id": 2, "quantity": "0"}, token=CUSTOMER_TOKEN, label="cart: update to 0 (removes)", expect=200)
req("post", "/api/cart/add", {"product_id": 3, "quantity": "1"}, token=CUSTOMER_TOKEN, label="cart: add another item")
req("post", "/api/cart/remove", {"product_id": 3}, token=CUSTOMER_TOKEN, label="cart: remove", expect=200)
req("post", "/api/cart/remove", {"product_id": 99999}, token=CUSTOMER_TOKEN, label="cart: remove nonexistent", expect=404)

# ── Addresses ──
req("get", "/api/addresses", token=CUSTOMER_TOKEN, label="addresses: list", expect=200)
r = req("post", "/api/address/add", {
    "latitude": "41.3111", "longitude": "69.2797",
    "address_text": "Test Address, Tashkent", "label": "Home",
}, token=CUSTOMER_TOKEN, label="address: add valid", expect=201)
if r and r[1] == 201:
    CREATED_IDS["address"] = r[0]["data"]["id"]

req("post", "/api/address/add", {}, token=CUSTOMER_TOKEN, label="address: add empty", expect=422)
req("post", "/api/address/add", {"latitude": "abc", "longitude": "69", "address_text": "x"}, token=CUSTOMER_TOKEN, label="address: add bad lat", expect=422)

if CREATED_IDS.get("address"):
    aid = CREATED_IDS["address"]
    req("patch", f"/api/address/{aid}/update", {"label": "Work"}, token=CUSTOMER_TOKEN, label="address: update", expect=200)
    req("post", f"/api/address/{aid}/default", token=CUSTOMER_TOKEN, label="address: set default", expect=200)
    req("patch", "/api/address/99999/update", {"label": "X"}, token=CUSTOMER_TOKEN, label="address: update nonexistent", expect=404)

# ── Orders ──
req("get", "/api/orders", token=CUSTOMER_TOKEN, label="orders: list", expect=200)
req("get", "/api/orders?status=pending", token=CUSTOMER_TOKEN, label="orders: filter by status", expect=200)
req("get", "/api/orders/active", token=CUSTOMER_TOKEN, label="orders: active", expect=200)
req("get", "/api/order/99999", token=CUSTOMER_TOKEN, label="order detail: nonexistent", expect=404)

# Place order — need cart items + address
req("post", "/api/cart/add", {"product_id": 2, "quantity": "1"}, token=CUSTOMER_TOKEN, label="cart: prep for order")
req("post", "/api/orders/place", {}, token=CUSTOMER_TOKEN, label="order: place empty body", expect=422)
req("post", "/api/orders/place", {"address_id": 99999, "payment_method": "cash"}, token=CUSTOMER_TOKEN, label="order: place bad address", expect=422)
req("post", "/api/orders/place", {"address_id": CREATED_IDS.get("address", 1), "payment_method": "bitcoin"}, token=CUSTOMER_TOKEN, label="order: place bad payment method", expect=422)

# Place order - no auth
req("post", "/api/orders/place", {"address_id": 1, "payment_method": "cash"}, label="order: place no auth", expect=401)

# Cancel nonexistent
req("post", "/api/order/99999/cancel", token=CUSTOMER_TOKEN, label="order cancel: nonexistent", expect=404)

# Reorder nonexistent
req("post", "/api/order/99999/reorder", token=CUSTOMER_TOKEN, label="reorder: nonexistent", expect=404)

# ── Favorites ──
req("get", "/api/favorites", token=CUSTOMER_TOKEN, label="favorites: list", expect=200)
req("post", "/api/favorite/2/toggle", token=CUSTOMER_TOKEN, label="favorite: toggle on", expect=200)
req("get", "/api/favorite/2/check", token=CUSTOMER_TOKEN, label="favorite: check", expect=200)
req("post", "/api/favorite/2/toggle", token=CUSTOMER_TOKEN, label="favorite: toggle off", expect=200)
req("post", "/api/favorite/99999/toggle", token=CUSTOMER_TOKEN, label="favorite: nonexistent product", expect=404)

# ── Reviews ──
req("get", "/api/reviews", token=CUSTOMER_TOKEN, label="reviews: list", expect=200)
req("post", "/api/review/submit", {"order_id": 99999, "rating": 5}, token=CUSTOMER_TOKEN, label="review: nonexistent order", expect=404)
req("post", "/api/review/submit", {"order_id": 1, "rating": 6}, token=CUSTOMER_TOKEN, label="review: rating > 5", expect=422)
req("post", "/api/review/submit", {"order_id": 1, "rating": 0}, token=CUSTOMER_TOKEN, label="review: rating < 1", expect=422)
req("post", "/api/review/submit", {}, token=CUSTOMER_TOKEN, label="review: empty body", expect=422)

# ── Notifications ──
req("get", "/api/notifications", token=CUSTOMER_TOKEN, label="notifications: list", expect=200)
req("get", "/api/notifications/unread-count", token=CUSTOMER_TOKEN, label="notifications: unread count", expect=200)
req("post", "/api/notifications/read-all", token=CUSTOMER_TOKEN, label="notifications: mark all read", expect=200)
req("post", "/api/notification/99999/read", token=CUSTOMER_TOKEN, label="notification: read nonexistent", expect=404)

# ── Referrals ──
req("get", "/api/referral", token=CUSTOMER_TOKEN, label="referral: my code", expect=200)
req("get", "/api/referral/list", token=CUSTOMER_TOKEN, label="referral: list", expect=200)
req("post", "/api/referral/apply", {"referral_code": ""}, token=CUSTOMER_TOKEN, label="referral: apply empty", expect=422)
req("post", "/api/referral/apply", {"referral_code": "ZZZZZZZZ"}, token=CUSTOMER_TOKEN, label="referral: apply invalid code", expect=422)

# ── Coupons ──
req("post", "/api/coupon/validate", {"code": "NONEXISTENT", "subtotal": "50000"}, token=CUSTOMER_TOKEN, label="coupon: validate invalid", expect=422)
req("post", "/api/coupon/validate", {}, token=CUSTOMER_TOKEN, label="coupon: empty body", expect=422)
req("post", "/api/coupon/validate", {"code": "X", "subtotal": "abc"}, token=CUSTOMER_TOKEN, label="coupon: bad subtotal", expect=422)

# ── Banners (public) ──
req("get", "/api/banners", label="banners: list", expect=200)

# ── Delivery (public) ──
req("get", "/api/delivery/check?lat=41.31&lng=69.27", label="delivery: check valid", expect=200)
req("get", "/api/delivery/check", label="delivery: no coords", expect=422)
req("get", "/api/delivery/check?lat=abc&lng=69", label="delivery: bad lat", expect=422)


# ═══════════════════════════════════════════════════
# ADMIN API TESTS
# ═══════════════════════════════════════════════════

print("\n" + "=" * 60)
print("ADMIN API TESTS")
print("=" * 60)

# Admin login
r = req("post", "/admin-api/auth-login", {"username": "admin", "password": "test1234"}, label="admin login: default creds")
if r and r[1] == 200:
    ADMIN_TOKEN = r[0]["data"]["session_key"]
else:
    # Try other common passwords
    for pw in ["admin", "admin123", "1234", "password"]:
        r = req("post", "/admin-api/auth-login", {"username": "admin", "password": pw}, label=f"admin login: try {pw}")
        if r and r[1] == 200:
            ADMIN_TOKEN = r[0]["data"]["session_key"]
            break

if not ADMIN_TOKEN:
    # Try cosmic user
    r = req("post", "/admin-api/auth-login", {"username": "cosmic", "password": "test1234"}, label="admin login: cosmic")
    if r and r[1] == 200:
        ADMIN_TOKEN = r[0]["data"]["session_key"]

if not ADMIN_TOKEN:
    print("WARNING: Could not get admin token, skipping admin tests")
    ADMIN_TOKEN = "invalid-token"

# Admin auth tests
req("post", "/admin-api/auth-login", {}, label="admin login: empty", expect=422)
req("post", "/admin-api/auth-login", {"username": "admin", "password": "wrong"}, label="admin login: wrong pw")
req("get", "/admin-api/auth-me", token=ADMIN_TOKEN, label="admin me")
# Skip logout-all to preserve admin token for remaining tests
# req("post", "/admin-api/auth-logout-all", token=ADMIN_TOKEN, label="admin logout-all")

# ── Users ──
req("get", "/admin-api/users", token=ADMIN_TOKEN, label="users: list", expect=200)
req("get", "/admin-api/users?q=test", token=ADMIN_TOKEN, label="users: search", expect=200)
req("get", "/admin-api/users?role=manager", token=ADMIN_TOKEN, label="users: filter role", expect=200)
req("get", "/admin-api/users?page=abc", token=ADMIN_TOKEN, label="users: bad page")
req("get", "/admin-api/user/1", token=ADMIN_TOKEN, label="user: get by id")
req("get", "/admin-api/user/99999", token=ADMIN_TOKEN, label="user: nonexistent")

# ── Customers ──
req("get", "/admin-api/customers", token=ADMIN_TOKEN, label="customers: list", expect=200)
req("get", "/admin-api/customers?q=test", token=ADMIN_TOKEN, label="customers: search")

# ── Categories ──
req("get", "/admin-api/categories", token=ADMIN_TOKEN, label="categories: list", expect=200)
req("get", "/admin-api/categories/tree", token=ADMIN_TOKEN, label="categories: tree", expect=200)
req("get", "/admin-api/category/1", token=ADMIN_TOKEN, label="category: get 1")
req("get", "/admin-api/category/99999", token=ADMIN_TOKEN, label="category: nonexistent")

# ── Products ──
req("get", "/admin-api/products", token=ADMIN_TOKEN, label="products: list", expect=200)
req("get", "/admin-api/products?q=olma&order_by=-price", token=ADMIN_TOKEN, label="products: search+order", expect=200)
req("get", "/admin-api/product/2", token=ADMIN_TOKEN, label="product: detail", expect=200)

# ── Orders ──
req("get", "/admin-api/orders", token=ADMIN_TOKEN, label="orders: list", expect=200)
req("get", "/admin-api/orders?status=pending", token=ADMIN_TOKEN, label="orders: filter pending", expect=200)

# ── Banners ──
req("get", "/admin-api/banners", token=ADMIN_TOKEN, label="banners: list", expect=200)

# ── Coupons ──
req("get", "/admin-api/coupons", token=ADMIN_TOKEN, label="coupons: list", expect=200)

# ── Discounts ──
req("get", "/admin-api/discounts", token=ADMIN_TOKEN, label="discounts: list", expect=200)

# ── Payments ──
req("get", "/admin-api/payments", token=ADMIN_TOKEN, label="payments: list", expect=200)

# ── Reviews ──
req("get", "/admin-api/reviews", token=ADMIN_TOKEN, label="reviews: list", expect=200)

# ── Notifications ──
req("get", "/admin-api/notifications", token=ADMIN_TOKEN, label="notifications: list", expect=200)

# ── Favorites ──
req("get", "/admin-api/favorites", token=ADMIN_TOKEN, label="favorites: list", expect=200)
req("get", "/admin-api/favorites/most", token=ADMIN_TOKEN, label="favorites: most favorited", expect=200)

# ── Permissions ──
req("get", "/admin-api/permissions", token=ADMIN_TOKEN, label="permissions: list", expect=200)
req("get", "/admin-api/permissions/groups", token=ADMIN_TOKEN, label="permission groups", expect=200)

# ── Settings ──
req("get", "/admin-api/settings", token=ADMIN_TOKEN, label="settings: list", expect=200)

# ── Addresses ──
req("get", "/admin-api/addresses", token=ADMIN_TOKEN, label="addresses: list", expect=200)

# ── Zones ──
req("get", "/admin-api/zones", token=ADMIN_TOKEN, label="zones: list", expect=200)

# ── Roles ──
req("get", "/admin-api/role/manager/permissions", token=ADMIN_TOKEN, label="role permissions: manager", expect=200)
req("get", "/admin-api/role/client/permissions", token=ADMIN_TOKEN, label="role permissions: client", expect=200)
req("get", "/admin-api/role/invalid/permissions", token=ADMIN_TOKEN, label="role permissions: invalid role", expect=422)

# ── Stats ──
for stat in ["overview", "staff", "customers", "orders", "products", "categories", "payments", "coupons", "discounts", "banners", "reviews", "notifications", "favorites", "zones"]:
    req("get", f"/admin-api/stats/{stat}", token=ADMIN_TOKEN, label=f"stats: {stat}", expect=200)

# ── Unauthorized access ──
req("get", "/admin-api/users", label="admin users: no auth", expect=401)
req("get", "/admin-api/orders", label="admin orders: no auth", expect=401)
req("get", "/admin-api/products", label="admin products: no auth", expect=401)
req("post", "/admin-api/product/create", {"name_uz": "x"}, label="admin create: no auth", expect=401)

# ── Customer token on admin endpoint ──
req("get", "/admin-api/users", token=CUSTOMER_TOKEN, label="admin users: customer token", expect=403)

# ── Injection / edge cases ──
req("get", "/api/products?q=' OR 1=1 --", label="SQL injection attempt in search", expect=200)
req("get", "/api/products?q=<script>alert(1)</script>", label="XSS attempt in search", expect=200)
req("get", "/api/products?order_by=; DROP TABLE products;", label="SQL injection in order_by", expect=200)
req("post", "/api/auth/login", {"phone": "' OR '1'='1", "password": "x"}, label="SQL injection in login", expect=401)
req("get", "/api/products?per_page=0", label="per_page=0", expect=200)
req("get", "/api/products?per_page=-1", label="per_page=-1", expect=200)
req("get", "/api/products?page=0", label="page=0", expect=200)
req("get", "/api/products?page=-1", label="page=-1", expect=200)

# Very long string
long_str = "A" * 10000
req("post", "/api/auth/register", {"phone": long_str, "first_name": long_str, "password": long_str}, label="register: very long strings")

# ── Cleanup: logout customer ──
req("post", "/api/auth/logout", token=CUSTOMER_TOKEN, label="customer logout")


# ═══════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════

print("\n\n")
print("=" * 80)
print("FULL TEST REPORT")
print("=" * 80)

passed = 0
failed = 0
errors_500 = 0
slow = []

for r in RESULTS:
    status = r.get("status", "?")
    ms = r.get("ms", 0)
    label = r.get("label", "")
    path = r.get("path", "")
    method = r.get("method", "?")
    detail = r.get("detail", "")
    ok = r.get("ok", True)

    icon = "✓" if ok else "✗"
    if status == 500 or status == "ERR":
        icon = "✗✗"
        errors_500 += 1
        failed += 1
    elif not ok:
        failed += 1
    else:
        passed += 1

    if ms > 500:
        slow.append(r)

    line = f"  {icon} [{status}] {ms:>7.1f}ms  {method:<6} {path:<45} {label}"
    if detail:
        line += f"  -- {detail[:80]}"
    print(line)

print("\n" + "=" * 80)
print(f"SUMMARY: {len(RESULTS)} tests | {passed} passed | {failed} failed | {errors_500} server errors (500)")
print("=" * 80)

if slow:
    print(f"\nSLOW REQUESTS (>500ms):")
    for r in slow:
        print(f"  {r['ms']:.0f}ms  {r['method']} {r['path']}  {r['label']}")

if errors_500:
    print(f"\nSERVER ERRORS (500):")
    for r in RESULTS:
        if r.get("status") == 500:
            print(f"  {r['method']} {r['path']}  {r['label']}")
            print(f"    {r.get('detail', '')[:200]}")

print(f"\nFAILED TESTS:")
for r in RESULTS:
    if not r.get("ok", True):
        print(f"  [{r['status']}] {r['method']} {r['path']}  {r['label']}  {r.get('detail', '')[:100]}")
