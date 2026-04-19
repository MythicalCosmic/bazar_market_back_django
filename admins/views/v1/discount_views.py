import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.discount import CreateDiscountDTO, UpdateDiscountDTO
from admins.services.v1.discount_service import DiscountService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _serialize_discount(d) -> dict:
    data = {
        "id": d.id,
        "uuid": str(d.uuid),
        "name_uz": d.name_uz,
        "name_ru": d.name_ru,
        "type": d.type,
        "value": str(d.value),
        "max_discount": str(d.max_discount) if d.max_discount else None,
        "starts_at": d.starts_at.isoformat() if d.starts_at else None,
        "expires_at": d.expires_at.isoformat() if d.expires_at else None,
        "is_active": d.is_active,
        "created_at": d.created_at.isoformat(),
    }
    if hasattr(d, "product_count"):
        data["product_count"] = d.product_count
    if hasattr(d, "category_count"):
        data["category_count"] = d.category_count
    if hasattr(d, "_products"):
        data["products"] = [
            {"id": p["id"], "name": p["name_uz"], "price": str(p["price"])}
            for p in d._products
        ]
    if hasattr(d, "_categories"):
        data["categories"] = [
            {"id": c["id"], "name": c["name_uz"]}
            for c in d._categories
        ]
    return data


def _parse_int_list(data, key):
    ids = data.get(key)
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return None
    return ids


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_DISCOUNTS)
def list_discounts_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(DiscountService)
    result = svc.get_all(
        query=request.GET.get("q"),
        is_active=_parse_bool(request.GET.get("is_active")),
        type=request.GET.get("type"),
        current_only=_parse_bool(request.GET.get("current_only")) or False,
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_discount(d) for d in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_DISCOUNTS)
def get_discount_view(request, discount_id):
    svc = container.resolve(DiscountService)
    discount = svc.get_by_id(discount_id)
    if not discount:
        return not_found("Discount not found")
    return success(data=_serialize_discount(discount))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def create_discount_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["name_uz", "type", "value"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateDiscountDTO(
        name_uz=data["name_uz"],
        type=data["type"],
        value=str(data["value"]),
        name_ru=data.get("name_ru", ""),
        max_discount=str(data["max_discount"]) if data.get("max_discount") is not None else None,
        starts_at=data.get("starts_at"),
        expires_at=data.get("expires_at"),
        is_active=data.get("is_active", True),
        product_ids=data.get("product_ids"),
        category_ids=data.get("category_ids"),
    )
    svc = container.resolve(DiscountService)
    result = svc.create_discount(dto)
    return created(data=result, message="Discount created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_DISCOUNTS)
def update_discount_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateDiscountDTO(**{k: v for k, v in data.items() if hasattr(UpdateDiscountDTO, k)})
    svc = container.resolve(DiscountService)
    result = svc.update_discount(discount_id, dto)
    return success(data=result, message="Discount updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_DISCOUNTS)
def delete_discount_view(request, discount_id):
    svc = container.resolve(DiscountService)
    return success(data=svc.delete_discount(discount_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def restore_discount_view(request, discount_id):
    svc = container.resolve(DiscountService)
    return success(data=svc.restore_discount(discount_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def activate_discount_view(request, discount_id):
    svc = container.resolve(DiscountService)
    return success(data=svc.activate(discount_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def deactivate_discount_view(request, discount_id):
    svc = container.resolve(DiscountService)
    return success(data=svc.deactivate(discount_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def set_discount_products_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = _parse_int_list(data, "product_ids")
    if ids is None:
        return error("product_ids must be a list of integers", status=422)

    svc = container.resolve(DiscountService)
    return success(data=svc.set_products(discount_id, ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def add_discount_products_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = _parse_int_list(data, "product_ids")
    if ids is None:
        return error("product_ids must be a list of integers", status=422)

    svc = container.resolve(DiscountService)
    return success(data=svc.add_products(discount_id, ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def remove_discount_products_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = _parse_int_list(data, "product_ids")
    if ids is None:
        return error("product_ids must be a list of integers", status=422)

    svc = container.resolve(DiscountService)
    return success(data=svc.remove_products(discount_id, ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def set_discount_categories_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = _parse_int_list(data, "category_ids")
    if ids is None:
        return error("category_ids must be a list of integers", status=422)

    svc = container.resolve(DiscountService)
    return success(data=svc.set_categories(discount_id, ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def add_discount_categories_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = _parse_int_list(data, "category_ids")
    if ids is None:
        return error("category_ids must be a list of integers", status=422)

    svc = container.resolve(DiscountService)
    return success(data=svc.add_categories(discount_id, ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DISCOUNTS)
def remove_discount_categories_view(request, discount_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = _parse_int_list(data, "category_ids")
    if ids is None:
        return error("category_ids must be a list of integers", status=422)

    svc = container.resolve(DiscountService)
    return success(data=svc.remove_categories(discount_id, ids))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def discount_stats_view(request):
    svc = container.resolve(DiscountService)
    return success(data=svc.stats())
