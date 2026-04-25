import json
import re

from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver


VIEW_METHOD = {
    "require_GET": "get",
    "require_POST": "post",
    "require_http_methods": "patch",
}

TAG_MAP = {
    "admin-api/": {
        "auth": "Admin Auth",
        "user": "Admin Users", "users": "Admin Users",
        "customer": "Admin Customers", "customers": "Admin Customers",
        "categor": "Admin Categories",
        "product": "Admin Products",
        "order": "Admin Orders",
        "banner": "Admin Banners",
        "coupon": "Admin Coupons",
        "discount": "Admin Discounts",
        "payment": "Admin Payments",
        "review": "Admin Reviews",
        "notification": "Admin Notifications",
        "role": "Admin Roles", "permission": "Admin Roles",
        "setting": "Admin Settings",
        "zone": "Admin Delivery Zones",
        "favorite": "Admin Favorites",
        "stat": "Admin Stats",
        "address": "Admin Addresses",
    },
    "api/": {
        "auth": "Customer Auth",
        "product": "Catalog", "categor": "Catalog",
        "cart": "Cart",
        "address": "Addresses",
        "order": "Orders",
        "favorite": "Favorites",
        "review": "Reviews",
        "notification": "Notifications",
        "referral": "Referrals",
        "coupon": "Coupons",
        "banner": "Banners",
        "delivery": "Delivery",
    },
}


def _guess_method(view_func):
    for attr in dir(view_func):
        if "initkwargs" in attr:
            pass
    name = getattr(view_func, "__name__", "")
    if "list_" in name or "get_" in name or "me_" in name or "check_" in name or "stats" in name or "search" in name or "tree" in name or "featured" in name or "popular" in name or "active_" in name or "unread_" in name:
        return "get"
    if "update_" in name:
        return "patch"
    if "delete_" in name and "account" not in name:
        return "delete"
    return "post"


def _guess_tag(prefix, route):
    tags = TAG_MAP.get(prefix, {})
    for keyword, tag in tags.items():
        if keyword in route:
            return tag
    return prefix.strip("/").replace("-", " ").title()


def _django_to_openapi_path(route):
    return re.sub(r"<(\w+:)?(\w+)>", r"{\2}", route)


def _extract_routes(resolver, prefix=""):
    routes = []
    for pattern in resolver.url_patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            routes.extend(_extract_routes(pattern, route))
        elif isinstance(pattern, URLPattern):
            view = pattern.callback
            name = pattern.name or getattr(view, "__name__", "")
            routes.append((route, view, name))
    return routes


class Command(BaseCommand):
    help = "Generate OpenAPI 3.0 spec from URL patterns"

    def add_arguments(self, parser):
        parser.add_argument("-o", "--output", default="base/openapi.json")
        parser.add_argument("--base-url", default="http://localhost:8000")

    def handle(self, *args, **options):
        resolver = get_resolver()
        routes = _extract_routes(resolver)

        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Bazar Market API",
                "version": "1.0.0",
                "description": "Admin API at /admin-api/, Customer API at /api/",
            },
            "servers": [{"url": options["base_url"]}],
            "paths": {},
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "description": "Session token from login",
                    }
                }
            },
        }

        skip = {"telescope/"}
        for route, view, name in routes:
            if any(s in route for s in skip):
                continue

            method = _guess_method(view)
            path = "/" + _django_to_openapi_path(route)

            # Determine prefix for tagging
            prefix = ""
            for p in ["admin-api/", "api/", "docs/"]:
                if route.startswith(p):
                    prefix = p
                    break

            tag = _guess_tag(prefix, route)
            requires_auth = "auth" not in route or "me" in route or "logout" in route or "verify" in route or "resend" in route

            # Check if public (catalog, banners, delivery, categories)
            public_patterns = ["api/products", "api/product/", "api/categories", "api/banners", "api/delivery"]
            is_public = any(route.startswith(p) for p in public_patterns)
            if "api/auth/login" in route or "api/auth/register" in route:
                is_public = True

            operation = {
                "tags": [tag],
                "operationId": name or view.__name__,
                "summary": (name or view.__name__).replace("_", " ").replace("-", " ").title(),
                "responses": {
                    "200": {"description": "Success"},
                    "401": {"description": "Unauthorized"},
                    "422": {"description": "Validation error"},
                },
            }

            if not is_public:
                operation["security"] = [{"BearerAuth": []}]

            # Path parameters
            params = re.findall(r"\{(\w+)\}", path)
            if params:
                operation["parameters"] = [
                    {"name": p, "in": "path", "required": True, "schema": {"type": "integer"}}
                    for p in params
                ]

            # Request body for POST/PATCH
            if method in ("post", "patch", "put") and "logout" not in name:
                operation["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }

            if path not in spec["paths"]:
                spec["paths"][path] = {}
            spec["paths"][path][method] = operation

        output_path = options["output"]
        with open(output_path, "w") as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)

        total = sum(len(methods) for methods in spec["paths"].values())
        self.stdout.write(self.style.SUCCESS(f"Generated {total} operations in {len(spec['paths'])} paths -> {output_path}"))
