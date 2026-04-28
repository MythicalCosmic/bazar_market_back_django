import json
import re
import uuid as _uuid

from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver


def _item(name, method, path, body=None, query=None, auth="bearer", events=None):
    """Build a single Postman request item."""
    segments = [s for s in path.strip("/").split("/") if s]

    url = {
        "raw": "{{base_url}}/" + path,
        "host": ["{{base_url}}"],
        "path": segments,
    }
    if query:
        url["query"] = [{"key": k, "value": v, "description": d} for k, v, d in query]

    req = {
        "method": method,
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "url": url,
    }

    if auth == "noauth":
        req["auth"] = {"type": "noauth"}

    if body is not None:
        req["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2, ensure_ascii=False),
            "options": {"raw": {"language": "json"}},
        }

    item = {"name": name, "request": req, "response": []}
    if events:
        item["event"] = events
    return item


# ── Auto-capture scripts ────────────────────────────────────────────
LOGIN_SCRIPT = {
    "listen": "test",
    "script": {
        "type": "text/javascript",
        "exec": [
            "if (pm.response.code === 200) {",
            "    var json = pm.response.json();",
            "    if (json.data && json.data.session_key) {",
            "        pm.collectionVariables.set('session_key', json.data.session_key);",
            "        console.log('session_key saved');",
            "    }",
            "}",
        ],
    },
}

CUSTOMER_LOGIN_SCRIPT = {
    "listen": "test",
    "script": {
        "type": "text/javascript",
        "exec": [
            "if (pm.response.code === 200) {",
            "    var json = pm.response.json();",
            "    if (json.data && json.data.session_key) {",
            "        pm.collectionVariables.set('customer_session_key', json.data.session_key);",
            "        console.log('customer_session_key saved');",
            "    }",
            "}",
        ],
    },
}


def _q(key, value="", desc=""):
    return (key, value, desc)


# ── Admin API Endpoints ─────────────────────────────────────────────
def _admin_folders():
    P = "admin-api"
    return [
        {
            "name": "Auth",
            "item": [
                _item("Login", "POST", f"{P}/auth-login",
                      body={"username": "admin", "password": "test1234", "device": "Postman"},
                      auth="noauth", events=[LOGIN_SCRIPT]),
                _item("Logout", "POST", f"{P}/auth-logout"),
                _item("Logout All", "POST", f"{P}/auth-logout-all"),
                _item("Me", "GET", f"{P}/auth-me"),
            ],
        },
        {
            "name": "Users",
            "item": [
                _item("List Users", "GET", f"{P}/users", query=[
                    _q("q", "", "Search by name/username/phone"),
                    _q("role", "", "admin|manager|courier"),
                    _q("is_active", "", "true|false"),
                    _q("is_deleted", "", "true for soft-deleted"),
                    _q("order_by", "-created_at", "created_at|first_name|last_name|role"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get User", "GET", f"{P}/user/1"),
                _item("Create User", "POST", f"{P}/user/create", body={
                    "username": "newuser", "first_name": "Test", "last_name": "User",
                    "role": "manager", "password": "test1234", "phone": "+998901111111",
                }),
                _item("Update User", "PATCH", f"{P}/user/1/update", body={"first_name": "Updated"}),
                _item("Delete User", "DELETE", f"{P}/user/1/delete"),
                _item("Restore User", "POST", f"{P}/user/1/restore"),
                _item("Get User Permissions", "GET", f"{P}/user/1/permissions"),
                _item("Grant User Permission", "POST", f"{P}/user/1/permissions/grant",
                      body={"permission": "manage_orders"}),
                _item("Deny User Permission", "POST", f"{P}/user/1/permissions/deny",
                      body={"permission": "manage_orders"}),
                _item("Remove User Permission Override", "DELETE", f"{P}/user/1/permissions/remove",
                      body={"permission": "manage_orders"}),
                _item("Clear User Permissions", "DELETE", f"{P}/user/1/permissions/clear"),
            ],
        },
        {
            "name": "Customers",
            "item": [
                _item("List Customers", "GET", f"{P}/customers", query=[
                    _q("q", "", "Search by name/phone/telegram"),
                    _q("is_active", "", "true|false"),
                    _q("order_by", "-created_at", "created_at|first_name|last_name"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Customer (Detail)", "GET", f"{P}/customer/1"),
                _item("Update Customer", "PATCH", f"{P}/customer/1/update",
                      body={"first_name": "Updated"}),
                _item("Deactivate Customer", "POST", f"{P}/customer/1/deactivate"),
                _item("Activate Customer", "POST", f"{P}/customer/1/activate"),
            ],
        },
        {
            "name": "Addresses",
            "item": [
                _item("List Addresses", "GET", f"{P}/addresses", query=[
                    _q("user_id", "", "Filter by user"),
                    _q("is_active", "", "true|false"),
                    _q("order_by", "-created_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("User Addresses", "GET", f"{P}/addresses/user/1"),
                _item("Get Address", "GET", f"{P}/address/1"),
            ],
        },
        {
            "name": "Categories",
            "item": [
                _item("List Categories", "GET", f"{P}/categories", query=[
                    _q("q", "", "Search by name"),
                    _q("is_active", "", "true|false"),
                    _q("parent_id", "", "Filter by parent"),
                    _q("is_deleted", "", "true for soft-deleted"),
                    _q("order_by", "sort_order"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Category Tree", "GET", f"{P}/categories/tree"),
                _item("Get Category", "GET", f"{P}/category/1"),
                _item("Create Category", "POST", f"{P}/category/create", body={
                    "name_uz": "Test kategoriya", "name_ru": "Тест категория",
                    "sort_order": 0, "is_active": True,
                }),
                _item("Update Category", "PATCH", f"{P}/category/1/update",
                      body={"name_uz": "Updated kategoriya"}),
                _item("Delete Category", "DELETE", f"{P}/category/1/delete"),
                _item("Restore Category", "POST", f"{P}/category/1/restore"),
                _item("Reorder Categories", "POST", f"{P}/categories/reorder",
                      body={"ids": [1, 2, 3]}),
                _item("Activate Category", "POST", f"{P}/category/1/activate"),
                _item("Deactivate Category", "POST", f"{P}/category/1/deactivate"),
            ],
        },
        {
            "name": "Products",
            "item": [
                _item("List Products", "GET", f"{P}/products", query=[
                    _q("q", "", "Search by name"),
                    _q("category_id", "", "Filter by category"),
                    _q("is_active", "", "true|false"),
                    _q("in_stock", "", "true|false"),
                    _q("is_featured", "", "true|false"),
                    _q("unit", "", "kg|piece|liter|pack|bundle"),
                    _q("min_price", ""), _q("max_price", ""),
                    _q("has_discount", "", "true|false"),
                    _q("stock_status", "", "low|out"),
                    _q("has_sku", "", "true|false"),
                    _q("has_barcode", "", "true|false"),
                    _q("order_by", "-created_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Product", "GET", f"{P}/product/1"),
                _item("Create Product", "POST", f"{P}/product/create", body={
                    "category_id": 1, "name_uz": "Test mahsulot", "unit": "kg",
                    "price": "15000", "step": "0.5", "min_qty": "0.5",
                    "sku": "TST-001", "barcode": "4901234567890",
                    "cost_price": "10000", "low_stock_threshold": "5",
                    "in_stock": True, "is_active": True,
                }),
                _item("Update Product", "PATCH", f"{P}/product/1/update",
                      body={"name_uz": "Updated mahsulot", "price": "18000"}),
                _item("Delete Product", "DELETE", f"{P}/product/1/delete"),
                _item("Restore Product", "POST", f"{P}/product/1/restore"),
                _item("Reorder Products", "POST", f"{P}/products/reorder",
                      body={"ids": [1, 2, 3]}),
                _item("Activate Product", "POST", f"{P}/product/1/activate"),
                _item("Deactivate Product", "POST", f"{P}/product/1/deactivate"),
                _item("Feature Product", "POST", f"{P}/product/1/feature"),
                _item("Unfeature Product", "POST", f"{P}/product/1/unfeature"),
                _item("Update Stock", "POST", f"{P}/product/1/stock",
                      body={"stock_qty": "100", "in_stock": True}),
                _item("Add Images", "POST", f"{P}/product/1/images",
                      body={"images": [{"image": "https://placehold.co/400x400?text=Test"}]}),
                _item("Remove Image", "DELETE", f"{P}/product/1/image/1"),
                _item("Reorder Images", "POST", f"{P}/product/1/images/reorder",
                      body={"ids": [1, 2]}),
                _item("Set Primary Image", "POST", f"{P}/product/1/image/1/primary"),
                _item("Assign Discounts", "POST", f"{P}/product/1/discounts/assign",
                      body={"discount_ids": [1]}),
                _item("Remove Discounts", "POST", f"{P}/product/1/discounts/remove",
                      body={"discount_ids": [1]}),
            ],
        },
        {
            "name": "Orders",
            "item": [
                _item("List Orders", "GET", f"{P}/orders", query=[
                    _q("q", "", "Search by order number/phone"),
                    _q("status", "", "pending|confirmed|preparing|delivering|delivered|completed|cancelled"),
                    _q("payment_status", "", "unpaid|pending|paid|refunded"),
                    _q("payment_method", "", "cash|card"),
                    _q("user_id", ""), _q("courier_id", ""),
                    _q("has_courier", "", "true|false"),
                    _q("date_from", "", "ISO datetime"), _q("date_to", "", "ISO datetime"),
                    _q("min_total", ""), _q("max_total", ""),
                    _q("order_by", "-created_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Order", "GET", f"{P}/order/1"),
                _item("Update Order Status", "POST", f"{P}/order/1/status",
                      body={"status": "confirmed", "note": "Confirmed via Postman"}),
                _item("Assign Courier", "POST", f"{P}/order/1/assign-courier",
                      body={"courier_id": 4}),
                _item("Unassign Courier", "POST", f"{P}/order/1/unassign-courier"),
                _item("Update Payment Status", "POST", f"{P}/order/1/payment-status",
                      body={"payment_status": "paid"}),
                _item("Add Admin Note", "POST", f"{P}/order/1/note",
                      body={"note": "Test note from Postman"}),
                _item("Cancel Order", "POST", f"{P}/order/1/cancel",
                      body={"reason": "Test cancel"}),
                _item("Bulk Update Status", "POST", f"{P}/orders/bulk-status",
                      body={"order_ids": [1, 2], "status": "confirmed"}),
                _item("Get Min Order", "GET", f"{P}/orders/min-order"),
                _item("Set Min Order", "POST", f"{P}/orders/min-order/set",
                      body={"amount": 30000}),
                _item("Accept & Print", "POST", f"{P}/order/1/accept-print"),
                _item("Print Order", "POST", f"{P}/order/1/print"),
            ],
        },
        {
            "name": "Banners",
            "item": [
                _item("List Banners", "GET", f"{P}/banners", query=[
                    _q("is_active", "", "true|false"),
                    _q("scheduled", "", "upcoming|active|expired"),
                    _q("order_by", "sort_order"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Banner", "GET", f"{P}/banner/1"),
                _item("Create Banner", "POST", f"{P}/banner/create", body={
                    "image": "https://placehold.co/800x400?text=Test", "title": "Test banner",
                    "link_type": "none", "sort_order": 0, "is_active": True,
                }),
                _item("Update Banner", "PATCH", f"{P}/banner/1/update",
                      body={"title": "Updated banner"}),
                _item("Delete Banner", "DELETE", f"{P}/banner/1/delete"),
                _item("Reorder Banners", "POST", f"{P}/banners/reorder",
                      body={"ids": [1, 2, 3]}),
                _item("Activate Banner", "POST", f"{P}/banner/1/activate"),
                _item("Deactivate Banner", "POST", f"{P}/banner/1/deactivate"),
            ],
        },
        {
            "name": "Coupons",
            "item": [
                _item("List Coupons", "GET", f"{P}/coupons", query=[
                    _q("q", "", "Search by code"),
                    _q("is_active", "", "true|false"),
                    _q("type", "", "percent|fixed"),
                    _q("valid_only", "", "true|false"),
                    _q("order_by", "-created_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Coupon", "GET", f"{P}/coupon/1"),
                _item("Create Coupon", "POST", f"{P}/coupon/create", body={
                    "code": "TESTCOUPON", "type": "percent", "value": 10,
                    "max_discount": 20000, "per_user_limit": 1, "is_active": True,
                }),
                _item("Update Coupon", "PATCH", f"{P}/coupon/1/update", body={"value": 15}),
                _item("Delete Coupon", "DELETE", f"{P}/coupon/1/delete"),
                _item("Activate Coupon", "POST", f"{P}/coupon/1/activate"),
                _item("Deactivate Coupon", "POST", f"{P}/coupon/1/deactivate"),
            ],
        },
        {
            "name": "Discounts",
            "item": [
                _item("List Discounts", "GET", f"{P}/discounts", query=[
                    _q("q", "", "Search by name"),
                    _q("is_active", "", "true|false"),
                    _q("type", "", "percent|fixed"),
                    _q("current_only", "", "true|false"),
                    _q("order_by", "-created_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Discount", "GET", f"{P}/discount/1"),
                _item("Create Discount", "POST", f"{P}/discount/create", body={
                    "name_uz": "Test chegirma", "type": "percent", "value": 10,
                    "is_active": True, "product_ids": [1], "category_ids": [1],
                }),
                _item("Update Discount", "PATCH", f"{P}/discount/1/update",
                      body={"name_uz": "Updated chegirma"}),
                _item("Delete Discount", "DELETE", f"{P}/discount/1/delete"),
                _item("Restore Discount", "POST", f"{P}/discount/1/restore"),
                _item("Activate Discount", "POST", f"{P}/discount/1/activate"),
                _item("Deactivate Discount", "POST", f"{P}/discount/1/deactivate"),
                _item("Set Discount Products", "POST", f"{P}/discount/1/products/set",
                      body={"product_ids": [1, 2]}),
                _item("Add Discount Products", "POST", f"{P}/discount/1/products/add",
                      body={"product_ids": [3]}),
                _item("Remove Discount Products", "POST", f"{P}/discount/1/products/remove",
                      body={"product_ids": [3]}),
                _item("Set Discount Categories", "POST", f"{P}/discount/1/categories/set",
                      body={"category_ids": [1]}),
                _item("Add Discount Categories", "POST", f"{P}/discount/1/categories/add",
                      body={"category_ids": [2]}),
                _item("Remove Discount Categories", "POST", f"{P}/discount/1/categories/remove",
                      body={"category_ids": [2]}),
            ],
        },
        {
            "name": "Delivery Zones",
            "item": [
                _item("List Zones", "GET", f"{P}/zones", query=[
                    _q("is_active", "", "true|false"),
                    _q("order_by", "sort_order"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Zone", "GET", f"{P}/zone/1"),
                _item("Create Zone", "POST", f"{P}/zone/create", body={
                    "name": "Test zona", "polygon": {"type": "Polygon", "coordinates": []},
                    "delivery_fee": "10000", "min_order": "50000", "estimated_minutes": 30,
                }),
                _item("Update Zone", "PATCH", f"{P}/zone/1/update", body={"name": "Updated zona"}),
                _item("Delete Zone", "DELETE", f"{P}/zone/1/delete"),
                _item("Reorder Zones", "POST", f"{P}/zones/reorder", body={"ids": [1, 2, 3]}),
                _item("Activate Zone", "POST", f"{P}/zone/1/activate"),
                _item("Deactivate Zone", "POST", f"{P}/zone/1/deactivate"),
            ],
        },
        {
            "name": "Reviews",
            "item": [
                _item("List Reviews", "GET", f"{P}/reviews", query=[
                    _q("q", "", "Search by comment/user/order"),
                    _q("rating", "", "1-5"),
                    _q("moderation_status", "", "pending|approved|rejected"),
                    _q("user_id", ""),
                    _q("order_by", "-created_at", "created_at|rating|moderation_status"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Review", "GET", f"{P}/review/1"),
                _item("Approve Review", "POST", f"{P}/review/1/approve"),
                _item("Reject Review", "POST", f"{P}/review/1/reject"),
                _item("Reply to Review", "POST", f"{P}/review/1/reply",
                      body={"reply": "Rahmat!"}),
                _item("Delete Review", "DELETE", f"{P}/review/1/delete"),
                _item("Bulk Approve", "POST", f"{P}/reviews/bulk-approve",
                      body={"review_ids": [1, 2]}),
                _item("Bulk Reject", "POST", f"{P}/reviews/bulk-reject",
                      body={"review_ids": [3]}),
            ],
        },
        {
            "name": "Payments",
            "item": [
                _item("List Payments", "GET", f"{P}/payments", query=[
                    _q("q", "", "Search by order_number/phone"),
                    _q("status", "", "pending|processing|completed|failed|refunded"),
                    _q("method", "", "cash|card"),
                    _q("order_id", ""),
                    _q("date_from", ""), _q("date_to", ""),
                    _q("min_amount", ""), _q("max_amount", ""),
                    _q("order_by", "-created_at", "created_at|amount|status|method|paid_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Payment", "GET", f"{P}/payment/1"),
                _item("Order Payments", "GET", f"{P}/payments/order/1"),
                _item("Update Payment Status", "POST", f"{P}/payment/1/status",
                      body={"status": "completed"}),
                _item("Refund Payment", "POST", f"{P}/payment/1/refund",
                      body={"reason": "Customer request"}),
            ],
        },
        {
            "name": "Notifications",
            "item": [
                _item("List Notifications", "GET", f"{P}/notifications", query=[
                    _q("q", "", "Search by title/body/user"),
                    _q("type", "", "order_status|promo|system"),
                    _q("channel", "", "telegram|sms|push"),
                    _q("is_read", "", "true|false"),
                    _q("user_id", ""),
                    _q("order_by", "-sent_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Notification", "GET", f"{P}/notification/1"),
                _item("Send to User", "POST", f"{P}/notification/user/1/send", body={
                    "title": "Test notification", "body": "Hello from Postman",
                    "type": "promo", "channel": "telegram",
                }),
                _item("Send Bulk", "POST", f"{P}/notifications/send", body={
                    "title": "Bulk test", "body": "Hello everyone",
                    "type": "promo", "channel": "telegram", "role": "client",
                }),
                _item("Delete Notification", "DELETE", f"{P}/notification/1/delete"),
                _item("Delete User Notifications", "DELETE", f"{P}/notification/user/1/delete"),
            ],
        },
        {
            "name": "Roles & Permissions",
            "item": [
                _item("List All Permissions", "GET", f"{P}/permissions", query=[
                    _q("group", "", "Filter by group"),
                ]),
                _item("List Permission Groups", "GET", f"{P}/permissions/groups"),
                _item("Sync Permissions", "POST", f"{P}/permissions/sync"),
                _item("Get Role Permissions", "GET", f"{P}/role/manager/permissions"),
                _item("Set Role Permissions", "POST", f"{P}/role/manager/permissions/set",
                      body={"permissions": ["view_orders", "view_users", "manage_orders"]}),
                _item("Reset Role to Defaults", "POST", f"{P}/role/manager/permissions/reset"),
            ],
        },
        {
            "name": "Settings",
            "item": [
                _item("List Settings", "GET", f"{P}/settings"),
                _item("Get Setting", "GET", f"{P}/setting/min_order_total"),
                _item("Set Setting", "POST", f"{P}/settings/set", body={
                    "key": "test_setting", "value": "hello", "type": "string",
                    "description": "Test setting from Postman",
                }),
                _item("Delete Setting", "DELETE", f"{P}/setting/test_setting/delete"),
            ],
        },
        {
            "name": "Favorites (Admin)",
            "item": [
                _item("List Favorites", "GET", f"{P}/favorites", query=[
                    _q("user_id", ""), _q("product_id", ""),
                    _q("order_by", "-created_at"),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Most Favorited Products", "GET", f"{P}/favorites/most", query=[
                    _q("limit", "20"),
                ]),
            ],
        },
        {
            "name": "Stats",
            "item": [
                _item("Overview", "GET", f"{P}/stats/overview", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Staff Stats", "GET", f"{P}/stats/staff", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Customer Stats", "GET", f"{P}/stats/customers", query=[
                    _q("date_from", ""), _q("date_to", ""),
                    _q("lat", "", "Reference latitude"), _q("lng", "", "Reference longitude"),
                ]),
                _item("Category Stats", "GET", f"{P}/stats/categories", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Product Stats", "GET", f"{P}/stats/products", query=[
                    _q("date_from", ""), _q("date_to", ""), _q("category_id", ""),
                ]),
                _item("Order Stats", "GET", f"{P}/stats/orders", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Banner Stats", "GET", f"{P}/stats/banners"),
                _item("Coupon Stats", "GET", f"{P}/stats/coupons", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Discount Stats", "GET", f"{P}/stats/discounts"),
                _item("Zone Stats", "GET", f"{P}/stats/zones"),
                _item("Review Stats", "GET", f"{P}/stats/reviews", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Payment Stats", "GET", f"{P}/stats/payments", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Notification Stats", "GET", f"{P}/stats/notifications", query=[
                    _q("date_from", ""), _q("date_to", ""),
                ]),
                _item("Favorite Stats", "GET", f"{P}/stats/favorites"),
            ],
        },
    ]


# ── Customer API Endpoints ──────────────────────────────────────────
def _customer_folders():
    P = "api"
    return [
        {
            "name": "Auth",
            "item": [
                _item("Register", "POST", f"{P}/auth/register", body={
                    "phone": "+998901234500", "first_name": "Test",
                    "password": "test1234", "device": "Postman",
                }, auth="noauth"),
                _item("Login", "POST", f"{P}/auth/login", body={
                    "phone": "+998911111101", "password": "test1234", "device": "Postman",
                }, auth="noauth", events=[CUSTOMER_LOGIN_SCRIPT]),
                _item("Logout", "POST", f"{P}/auth/logout"),
                _item("Logout All", "POST", f"{P}/auth/logout-all"),
                _item("Verify Phone", "POST", f"{P}/auth/verify", body={"code": "123456"}),
                _item("Resend Code", "POST", f"{P}/auth/resend-code"),
                _item("Me", "GET", f"{P}/auth/me"),
                _item("Update Profile", "PATCH", f"{P}/auth/me/update",
                      body={"first_name": "Updated", "language": "ru"}),
                _item("Delete Account", "POST", f"{P}/auth/me/delete"),
            ],
        },
        {
            "name": "Catalog",
            "item": [
                _item("List Products", "GET", f"{P}/products", query=[
                    _q("category_id", ""), _q("q", "", "Search"),
                    _q("is_featured", "", "true|false"),
                    _q("order_by", "sort_order"),
                    _q("page", "1"), _q("per_page", "20"),
                ], auth="noauth"),
                _item("Get Product", "GET", f"{P}/product/1", auth="noauth"),
                _item("Featured Products", "GET", f"{P}/products/featured", query=[
                    _q("page", "1"), _q("per_page", "20"),
                ], auth="noauth"),
                _item("Popular Products", "GET", f"{P}/products/popular", query=[
                    _q("page", "1"), _q("per_page", "20"),
                ], auth="noauth"),
                _item("Search Products", "GET", f"{P}/products/search", query=[
                    _q("q", "olma", "Search query (required)"),
                    _q("page", "1"), _q("per_page", "20"),
                ], auth="noauth"),
                _item("List Categories", "GET", f"{P}/categories", auth="noauth"),
                _item("Category Tree", "GET", f"{P}/categories/tree", auth="noauth"),
                _item("Banners", "GET", f"{P}/banners", auth="noauth"),
            ],
        },
        {
            "name": "Cart",
            "item": [
                _item("Get Cart", "GET", f"{P}/cart"),
                _item("Add to Cart", "POST", f"{P}/cart/add",
                      body={"product_id": 1, "quantity": 2}),
                _item("Update Cart Item", "POST", f"{P}/cart/update",
                      body={"product_id": 1, "quantity": 5}),
                _item("Remove from Cart", "POST", f"{P}/cart/remove",
                      body={"product_id": 1}),
                _item("Clear Cart", "POST", f"{P}/cart/clear"),
            ],
        },
        {
            "name": "Addresses",
            "item": [
                _item("List My Addresses", "GET", f"{P}/addresses"),
                _item("Add Address", "POST", f"{P}/address/add", body={
                    "latitude": "41.2856", "longitude": "69.2042",
                    "address_text": "Chilanzar 9, dom 45", "label": "Uy",
                    "is_default": True,
                }),
                _item("Update Address", "PATCH", f"{P}/address/1/update",
                      body={"label": "Ish", "address_text": "Amir Temur 108"}),
                _item("Delete Address", "POST", f"{P}/address/1/delete"),
                _item("Set Default Address", "POST", f"{P}/address/1/default"),
            ],
        },
        {
            "name": "Orders",
            "item": [
                _item("Place Order", "POST", f"{P}/orders/place", body={
                    "address_id": 1, "payment_method": "cash",
                    "user_note": "Tezroq yetkazing", "coupon_code": "YANGI2026",
                }),
                _item("List My Orders", "GET", f"{P}/orders", query=[
                    _q("status", "", "pending|confirmed|..."),
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Get Order", "GET", f"{P}/order/1"),
                _item("Active Orders", "GET", f"{P}/orders/active"),
                _item("Cancel Order", "POST", f"{P}/order/1/cancel",
                      body={"reason": "Changed my mind"}),
                _item("Reorder", "POST", f"{P}/order/1/reorder"),
            ],
        },
        {
            "name": "Favorites",
            "item": [
                _item("List Favorites", "GET", f"{P}/favorites", query=[
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Toggle Favorite", "POST", f"{P}/favorite/1/toggle"),
                _item("Check Favorite", "GET", f"{P}/favorite/1/check"),
            ],
        },
        {
            "name": "Reviews",
            "item": [
                _item("Submit Review", "POST", f"{P}/review/submit",
                      body={"order_id": 1, "rating": 5, "comment": "Juda yaxshi!"}),
                _item("My Reviews", "GET", f"{P}/reviews", query=[
                    _q("page", "1"), _q("per_page", "20"),
                ]),
            ],
        },
        {
            "name": "Notifications",
            "item": [
                _item("List Notifications", "GET", f"{P}/notifications"),
                _item("Mark as Read", "POST", f"{P}/notification/1/read"),
                _item("Mark All Read", "POST", f"{P}/notifications/read-all"),
                _item("Unread Count", "GET", f"{P}/notifications/unread-count"),
            ],
        },
        {
            "name": "Referrals",
            "item": [
                _item("My Referral", "GET", f"{P}/referral"),
                _item("Referral List", "GET", f"{P}/referral/list", query=[
                    _q("page", "1"), _q("per_page", "20"),
                ]),
                _item("Apply Referral", "POST", f"{P}/referral/apply",
                      body={"referral_code": "ABC123"}),
            ],
        },
        {
            "name": "Coupons",
            "item": [
                _item("Validate Coupon", "POST", f"{P}/coupon/validate",
                      body={"code": "YANGI2026", "subtotal": "150000"}),
            ],
        },
        {
            "name": "Delivery",
            "item": [
                _item("Check Delivery", "GET", f"{P}/delivery/check", query=[
                    _q("lat", "41.2856", "Latitude"),
                    _q("lng", "69.2042", "Longitude"),
                ], auth="noauth"),
            ],
        },
    ]


class Command(BaseCommand):
    help = "Export all API routes as a Postman v2.1 collection JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "-o", "--output",
            default="postman_collection.json",
            help="Output file path (default: postman_collection.json)",
        )
        parser.add_argument(
            "--base-url",
            default="http://localhost",
            help="Base URL value for the Postman variable (default: http://localhost)",
        )

    def handle(self, *args, **options):
        admin_folders = _admin_folders()
        customer_folders = _customer_folders()

        admin_total = sum(len(f["item"]) for f in admin_folders)
        customer_total = sum(len(f["item"]) for f in customer_folders)

        # Health check as top-level
        health = _item("Health Check", "GET", "health", auth="noauth")

        collection = {
            "info": {
                "_postman_id": str(_uuid.uuid4()),
                "name": "Bazar Market API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "variable": [
                {"key": "base_url", "value": options["base_url"]},
                {"key": "session_key", "value": "", "description": "Admin session token (auto-set on login)"},
                {"key": "customer_session_key", "value": "", "description": "Customer session token (auto-set on login)"},
            ],
            "auth": {
                "type": "bearer",
                "bearer": [{"key": "token", "value": "{{session_key}}", "type": "string"}],
            },
            "item": [
                health,
                {
                    "name": "Admin API",
                    "item": admin_folders,
                    "auth": {
                        "type": "bearer",
                        "bearer": [{"key": "token", "value": "{{session_key}}", "type": "string"}],
                    },
                },
                {
                    "name": "Customer API",
                    "item": customer_folders,
                    "auth": {
                        "type": "bearer",
                        "bearer": [{"key": "token", "value": "{{customer_session_key}}", "type": "string"}],
                    },
                },
            ],
        }

        output_path = options["output"]
        with open(output_path, "w") as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {admin_total + customer_total + 1} requests → {output_path}\n"
            f"  Admin API:    {admin_total} requests in {len(admin_folders)} folders\n"
            f"  Customer API: {customer_total} requests in {len(customer_folders)} folders\n"
            f"  + Health Check"
        ))
