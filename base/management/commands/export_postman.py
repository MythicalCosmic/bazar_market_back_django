import json
import uuid

from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver


BASE_URL = "{{base_url}}"
AUTH_HEADER = "Bearer {{session_key}}"

# Map view function names to (method, body|None)
# Views using @require_GET -> GET, @require_POST -> POST,
# @require_http_methods(["PATCH"]) -> PATCH, ["DELETE"] -> DELETE
VIEW_META = {
    # Auth
    "login_view": ("POST", {"username": "admin", "password": "test1234", "device": "Postman"}),
    "logout_view": ("POST", None),
    "logout_all_view": ("POST", None),
    "me_view": ("GET", None),

    # Users
    "list_users_view": ("GET", None),
    "get_user_view": ("GET", None),
    "create_user_view": ("POST", {
        "username": "newuser", "first_name": "Test", "last_name": "User",
        "role": "manager", "password": "test1234", "phone": "+998901111111",
    }),
    "update_user_view": ("PATCH", {"first_name": "Updated"}),
    "delete_user_view": ("DELETE", None),
    "restore_user_view": ("POST", None),

    # Customers
    "list_customers_view": ("GET", None),
    "get_customer_view": ("GET", None),
    "update_customer_view": ("PATCH", {"first_name": "Updated"}),
    "deactivate_customer_view": ("POST", None),
    "activate_customer_view": ("POST", None),

    # Addresses
    "list_addresses_view": ("GET", None),
    "user_addresses_view": ("GET", None),
    "get_address_view": ("GET", None),

    # Categories
    "list_categories_view": ("GET", None),
    "get_category_view": ("GET", None),
    "category_tree_view": ("GET", None),
    "create_category_view": ("POST", {
        "name_uz": "Test kategoriya", "name_ru": "Тест категория",
        "sort_order": 0, "is_active": True,
    }),
    "update_category_view": ("PATCH", {"name_uz": "Updated kategoriya"}),
    "delete_category_view": ("DELETE", None),
    "restore_category_view": ("POST", None),
    "reorder_categories_view": ("POST", {"ids": [1, 2, 3]}),
    "activate_category_view": ("POST", None),
    "deactivate_category_view": ("POST", None),

    # Products
    "list_products_view": ("GET", None),
    "get_product_view": ("GET", None),
    "create_product_view": ("POST", {
        "category_id": 1, "name_uz": "Test mahsulot", "unit": "kg",
        "price": "15000", "step": "0.5", "min_qty": "0.5",
        "in_stock": True, "is_active": True,
    }),
    "update_product_view": ("PATCH", {"name_uz": "Updated mahsulot"}),
    "delete_product_view": ("DELETE", None),
    "restore_product_view": ("POST", None),
    "reorder_products_view": ("POST", {"ids": [1, 2, 3]}),
    "activate_product_view": ("POST", None),
    "deactivate_product_view": ("POST", None),
    "feature_product_view": ("POST", None),
    "unfeature_product_view": ("POST", None),
    "update_stock_view": ("POST", {"stock_qty": "100", "in_stock": True}),
    "add_images_view": ("POST", {"images": [{"image": "https://placehold.co/400x400?text=Test"}]}),
    "remove_image_view": ("DELETE", None),
    "reorder_images_view": ("POST", {"ids": [1, 2]}),
    "set_primary_image_view": ("POST", None),
    "assign_discounts_view": ("POST", {"discount_ids": [1]}),
    "remove_discounts_view": ("POST", {"discount_ids": [1]}),

    # Orders
    "list_orders_view": ("GET", None),
    "get_order_view": ("GET", None),
    "update_order_status_view": ("POST", {"status": "confirmed", "note": "Confirmed via Postman"}),
    "assign_courier_view": ("POST", {"courier_id": 4}),
    "unassign_courier_view": ("POST", None),
    "update_payment_status_view": ("POST", {"payment_status": "paid"}),
    "add_admin_note_view": ("POST", {"note": "Test note from Postman"}),
    "cancel_order_view": ("POST", {"reason": "Test cancel"}),
    "bulk_update_status_view": ("POST", {"order_ids": [1, 2], "status": "confirmed"}),
    "get_min_order_view": ("GET", None),
    "set_min_order_view": ("POST", {"amount": 30000}),

    # Banners
    "list_banners_view": ("GET", None),
    "get_banner_view": ("GET", None),
    "create_banner_view": ("POST", {
        "image": "https://placehold.co/800x400?text=Test", "title": "Test banner",
        "link_type": "none", "sort_order": 0, "is_active": True,
    }),
    "update_banner_view": ("PATCH", {"title": "Updated banner"}),
    "delete_banner_view": ("DELETE", None),
    "reorder_banners_view": ("POST", {"ids": [1, 2, 3]}),
    "activate_banner_view": ("POST", None),
    "deactivate_banner_view": ("POST", None),

    # Coupons
    "list_coupons_view": ("GET", None),
    "get_coupon_view": ("GET", None),
    "create_coupon_view": ("POST", {
        "code": "TESTCOUPON", "type": "percent", "value": 10,
        "max_discount": 20000, "per_user_limit": 1, "is_active": True,
    }),
    "update_coupon_view": ("PATCH", {"value": 15}),
    "delete_coupon_view": ("DELETE", None),
    "activate_coupon_view": ("POST", None),
    "deactivate_coupon_view": ("POST", None),

    # Discounts
    "list_discounts_view": ("GET", None),
    "get_discount_view": ("GET", None),
    "create_discount_view": ("POST", {
        "name_uz": "Test chegirma", "type": "percent", "value": 10,
        "is_active": True,
    }),
    "update_discount_view": ("PATCH", {"name_uz": "Updated chegirma"}),
    "delete_discount_view": ("DELETE", None),
    "restore_discount_view": ("POST", None),
    "activate_discount_view": ("POST", None),
    "deactivate_discount_view": ("POST", None),
    "set_discount_products_view": ("POST", {"product_ids": [1, 2]}),
    "add_discount_products_view": ("POST", {"product_ids": [3]}),
    "remove_discount_products_view": ("POST", {"product_ids": [3]}),
    "set_discount_categories_view": ("POST", {"category_ids": [1]}),
    "add_discount_categories_view": ("POST", {"category_ids": [2]}),
    "remove_discount_categories_view": ("POST", {"category_ids": [2]}),

    # Delivery Zones
    "list_zones_view": ("GET", None),
    "get_zone_view": ("GET", None),
    "create_zone_view": ("POST", {
        "name": "Test zona", "polygon": {"type": "Polygon", "coordinates": []},
        "delivery_fee": "10000", "min_order": "50000", "estimated_minutes": 30,
    }),
    "update_zone_view": ("PATCH", {"name": "Updated zona"}),
    "delete_zone_view": ("DELETE", None),
    "reorder_zones_view": ("POST", {"ids": [1, 2, 3]}),
    "activate_zone_view": ("POST", None),
    "deactivate_zone_view": ("POST", None),

    # Reviews
    "list_reviews_view": ("GET", None),
    "get_review_view": ("GET", None),
    "approve_review_view": ("POST", None),
    "reject_review_view": ("POST", None),
    "reply_review_view": ("POST", {"reply": "Rahmat!"}),
    "delete_review_view": ("DELETE", None),
    "bulk_approve_reviews_view": ("POST", {"review_ids": [1, 2]}),
    "bulk_reject_reviews_view": ("POST", {"review_ids": [3]}),

    # Payments
    "list_payments_view": ("GET", None),
    "get_payment_view": ("GET", None),
    "order_payments_view": ("GET", None),
    "update_payment_view": ("POST", {"status": "completed"}),
    "refund_payment_view": ("POST", {"reason": "Customer request"}),

    # Notifications
    "list_notifications_view": ("GET", None),
    "get_notification_view": ("GET", None),
    "send_notification_view": ("POST", {
        "title": "Test notification", "body": "Hello from Postman",
        "type": "promo", "channel": "telegram",
    }),
    "send_bulk_notification_view": ("POST", {
        "title": "Bulk test", "body": "Hello everyone",
        "type": "promo", "channel": "telegram", "role": "client",
    }),
    "delete_notification_view": ("DELETE", None),
    "delete_user_notifications_view": ("DELETE", None),

    # Roles & Permissions
    "list_permissions_view": ("GET", None),
    "list_permission_groups_view": ("GET", None),
    "get_role_permissions_view": ("GET", None),
    "set_role_permissions_view": ("POST", {"permissions": ["view_orders", "view_users"]}),
    "reset_role_permissions_view": ("POST", None),
    "get_user_permissions_view": ("GET", None),
    "grant_user_permission_view": ("POST", {"permission": "manage_orders"}),
    "deny_user_permission_view": ("POST", {"permission": "manage_orders"}),
    "remove_user_permission_view": ("DELETE", {"permission": "manage_orders"}),
    "clear_user_permissions_view": ("DELETE", None),
    "sync_permissions_view": ("POST", None),

    # Settings
    "list_settings_view": ("GET", None),
    "get_setting_view": ("GET", None),
    "set_setting_view": ("POST", {
        "key": "test_setting", "value": "hello", "type": "string",
        "description": "Test setting from Postman",
    }),
    "delete_setting_view": ("DELETE", None),

    # Favorites
    "list_favorites_view": ("GET", None),
    "most_favorited_view": ("GET", None),

    # Stats
    "staff_stats_view": ("GET", None),
    "customer_stats_view": ("GET", None),
    "overview_view": ("GET", None),
    "category_stats_view": ("GET", None),
    "product_stats_view": ("GET", None),
    "order_stats_view": ("GET", None),
    "banner_stats_view": ("GET", None),
    "coupon_stats_view": ("GET", None),
    "discount_stats_view": ("GET", None),
    "zone_stats_view": ("GET", None),
    "review_stats_view": ("GET", None),
    "payment_stats_view": ("GET", None),
    "notification_stats_view": ("GET", None),
    "favorite_stats_view": ("GET", None),
}

# URL name -> folder name mapping
FOLDER_MAP = {
    "login": "Auth", "logout": "Auth", "logout-all": "Auth", "me": "Auth",
    "users": "Users", "user": "Users", "create": "Users", "update": "Users",
    "delete": "Users", "restore": "Users",
    "customers": "Customers", "customer": "Customers",
    "customer-update": "Customers", "customer-deactivate": "Customers",
    "customer-activate": "Customers",
    "addresses": "Addresses", "user-addresses": "Addresses", "address": "Addresses",
    "categories": "Categories", "category": "Categories", "categories-tree": "Categories",
    "categories-reorder": "Categories", "category-create": "Categories",
    "category-update": "Categories", "category-delete": "Categories",
    "category-restore": "Categories", "category-activate": "Categories",
    "category-deactivate": "Categories",
    "products": "Products", "product": "Products", "products-reorder": "Products",
    "product-create": "Products", "product-update": "Products",
    "product-delete": "Products", "product-restore": "Products",
    "product-activate": "Products", "product-deactivate": "Products",
    "product-feature": "Products", "product-unfeature": "Products",
    "product-stock": "Products", "product-images-add": "Products",
    "product-images-reorder": "Products", "product-image-remove": "Products",
    "product-image-primary": "Products",
    "product-discounts-assign": "Products", "product-discounts-remove": "Products",
    "orders": "Orders", "order": "Orders", "orders-bulk-status": "Orders",
    "orders-min-order-get": "Orders", "orders-min-order-set": "Orders",
    "order-status": "Orders", "order-assign-courier": "Orders",
    "order-unassign-courier": "Orders", "order-payment-status": "Orders",
    "order-note": "Orders", "order-cancel": "Orders",
    "banners": "Banners", "banner": "Banners", "banners-reorder": "Banners",
    "banner-create": "Banners", "banner-update": "Banners",
    "banner-delete": "Banners", "banner-activate": "Banners",
    "banner-deactivate": "Banners",
    "coupons": "Coupons", "coupon": "Coupons", "coupon-create": "Coupons",
    "coupon-update": "Coupons", "coupon-delete": "Coupons",
    "coupon-activate": "Coupons", "coupon-deactivate": "Coupons",
    "discounts": "Discounts", "discount": "Discounts",
    "discount-create": "Discounts", "discount-update": "Discounts",
    "discount-delete": "Discounts", "discount-restore": "Discounts",
    "discount-activate": "Discounts", "discount-deactivate": "Discounts",
    "discount-products-set": "Discounts", "discount-products-add": "Discounts",
    "discount-products-remove": "Discounts", "discount-categories-set": "Discounts",
    "discount-categories-add": "Discounts", "discount-categories-remove": "Discounts",
    "zones": "Delivery Zones", "zone": "Delivery Zones",
    "zones-reorder": "Delivery Zones", "zone-create": "Delivery Zones",
    "zone-update": "Delivery Zones", "zone-delete": "Delivery Zones",
    "zone-activate": "Delivery Zones", "zone-deactivate": "Delivery Zones",
    "reviews": "Reviews", "review": "Reviews",
    "reviews-bulk-approve": "Reviews", "reviews-bulk-reject": "Reviews",
    "review-approve": "Reviews", "review-reject": "Reviews",
    "review-reply": "Reviews", "review-delete": "Reviews",
    "payments": "Payments", "payment": "Payments",
    "payment-status": "Payments", "payment-refund": "Payments",
    "payments-by-order": "Payments",
    "notifications": "Notifications", "notification": "Notifications",
    "notifications-send-bulk": "Notifications",
    "notification-send": "Notifications", "notification-delete": "Notifications",
    "notification-user-delete": "Notifications",
    "permissions": "Roles & Permissions", "permission-groups": "Roles & Permissions",
    "permissions-sync": "Roles & Permissions",
    "role-permissions": "Roles & Permissions",
    "role-permissions-set": "Roles & Permissions",
    "role-permissions-reset": "Roles & Permissions",
    "user-permissions": "Roles & Permissions",
    "user-permission-grant": "Roles & Permissions",
    "user-permission-deny": "Roles & Permissions",
    "user-permission-remove": "Roles & Permissions",
    "user-permissions-clear": "Roles & Permissions",
    "settings": "Settings", "setting": "Settings",
    "settings-set": "Settings", "setting-delete": "Settings",
    "favorites": "Favorites", "favorites-most": "Favorites",
}

STATS_NAMES = {
    "stats-overview", "stats-staff", "stats-customers", "stats-categories",
    "stats-products", "stats-orders", "stats-banners", "stats-coupons",
    "stats-discounts", "stats-zones", "stats-reviews", "stats-payments",
    "stats-notifications", "stats-favorites",
}

SAMPLE_IDS = {
    "user_id": 1,
    "customer_id": 1,
    "address_id": 1,
    "category_id": 1,
    "product_id": 1,
    "image_id": 1,
    "order_id": 1,
    "banner_id": 1,
    "coupon_id": 1,
    "discount_id": 1,
    "zone_id": 1,
    "review_id": 1,
    "payment_id": 1,
    "notification_id": 1,
}


class Command(BaseCommand):
    help = "Export all admin API routes as a Postman v2.1 collection JSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "-o", "--output",
            default="postman_collection.json",
            help="Output file path (default: postman_collection.json)",
        )
        parser.add_argument(
            "--base-url",
            default="http://localhost:8000",
            help="Base URL value for the Postman variable (default: http://localhost:8000)",
        )

    def handle(self, *args, **options):
        resolver = get_resolver()
        items_by_folder = {}

        self._walk(resolver, prefix="", items_by_folder=items_by_folder)

        folders = []
        folder_order = []
        for folder_name, items in items_by_folder.items():
            if folder_name not in folder_order:
                folder_order.append(folder_name)

        for folder_name in folder_order:
            folders.append({
                "name": folder_name,
                "item": items_by_folder[folder_name],
            })

        collection = {
            "info": {
                "_postman_id": str(uuid.uuid4()),
                "name": "Bazar Market Admin API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "variable": [
                {"key": "base_url", "value": options["base_url"]},
                {"key": "session_key", "value": ""},
            ],
            "auth": {
                "type": "bearer",
                "bearer": [{"key": "token", "value": "{{session_key}}", "type": "string"}],
            },
            "event": [
                {
                    "listen": "prerequest",
                    "script": {"type": "text/javascript", "exec": [""]},
                },
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            "// Auto-capture session_key from login response",
                            "if (pm.info.requestName === 'Login' && pm.response.code === 200) {",
                            "    var json = pm.response.json();",
                            "    if (json.data && json.data.session_key) {",
                            "        pm.collectionVariables.set('session_key', json.data.session_key);",
                            "        console.log('session_key saved: ' + json.data.session_key);",
                            "    }",
                            "}",
                        ],
                    },
                },
            ],
            "item": folders,
        }

        output_path = options["output"]
        with open(output_path, "w") as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)

        total = sum(len(items) for items in items_by_folder.values())
        self.stdout.write(self.style.SUCCESS(
            f"Exported {total} requests in {len(folders)} folders → {output_path}"
        ))

    def _walk(self, resolver, prefix, items_by_folder):
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                new_prefix = prefix + str(pattern.pattern)
                self._walk(pattern, new_prefix, items_by_folder)
            elif isinstance(pattern, URLPattern):
                self._add_pattern(pattern, prefix, items_by_folder)

    def _add_pattern(self, pattern, prefix, items_by_folder):
        url_name = pattern.name
        if not url_name:
            return

        callback = pattern.callback
        view_name = getattr(callback, "__name__", None)
        if not view_name:
            return

        meta = VIEW_META.get(view_name)
        if meta is None:
            return

        method, body = meta

        raw_path = prefix + str(pattern.pattern)
        # Replace Django URL params <type:name> with Postman :name
        path = self._django_to_postman_path(raw_path)
        # Build display name from url_name
        display_name = self._make_name(url_name, view_name)

        # Determine folder
        if url_name in STATS_NAMES:
            folder = "Stats"
        else:
            folder = FOLDER_MAP.get(url_name, "Other")

        if folder not in items_by_folder:
            items_by_folder[folder] = []

        # Build path segments for Postman
        segments = [s for s in path.strip("/").split("/") if s]
        postman_path = segments

        # Build request
        request = {
            "method": method,
            "header": [
                {"key": "Content-Type", "value": "application/json"},
            ],
            "url": {
                "raw": f"{BASE_URL}/{path}",
                "host": ["{{base_url}}"],
                "path": postman_path,
            },
        }

        # No auth header for login
        if view_name == "login_view":
            request["auth"] = {"type": "noauth"}

        if body is not None:
            request["body"] = {
                "mode": "raw",
                "raw": json.dumps(body, indent=2, ensure_ascii=False),
                "options": {"raw": {"language": "json"}},
            }

        item = {
            "name": display_name,
            "request": request,
            "response": [],
        }

        # Add test script for login to auto-save session_key
        if view_name == "login_view":
            item["event"] = [
                {
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
                },
            ]

        items_by_folder[folder].append(item)

    def _django_to_postman_path(self, path):
        import re
        # <int:user_id> -> :user_id  but use sample values for Postman
        def _replace(match):
            param_type = match.group(1)
            param_name = match.group(2)
            sample = SAMPLE_IDS.get(param_name)
            if sample is not None:
                return str(sample)
            if param_name == "role":
                return "manager"
            if param_name == "key":
                return "test_setting"
            return f":{param_name}"

        return re.sub(r"<(\w+):(\w+)>", _replace, path)

    def _make_name(self, url_name, view_name):
        name = url_name.replace("-", " ").replace("_", " ").title()
        return name
