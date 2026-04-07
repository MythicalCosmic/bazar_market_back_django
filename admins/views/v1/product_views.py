import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.product import CreateProductDTO, UpdateProductDTO
from admins.services.v1.product_service import ProductService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _parse_decimal(value):
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _serialize_product(p) -> dict:
    data = {
        "id": p.id,
        "uuid": str(p.uuid),
        "category_id": p.category_id,
        "category_name": p.category.name_uz if hasattr(p, "category") and p.category else None,
        "name_uz": p.name_uz,
        "name_ru": p.name_ru,
        "sku": p.sku,
        "barcode": p.barcode,
        "unit": p.unit,
        "price": str(p.price),
        "cost_price": str(p.cost_price) if p.cost_price is not None else None,
        "margin": p.margin,
        "in_stock": p.in_stock,
        "stock_qty": str(p.stock_qty) if p.stock_qty is not None else None,
        "low_stock_threshold": str(p.low_stock_threshold) if p.low_stock_threshold is not None else None,
        "is_low_stock": p.is_low_stock,
        "sort_order": p.sort_order,
        "is_active": p.is_active,
        "is_featured": p.is_featured,
        "created_at": p.created_at.isoformat(),
    }
    if hasattr(p, "primary_image"):
        data["primary_image"] = p.primary_image
    return data


def _serialize_product_detail(p) -> dict:
    data = _serialize_product(p)
    data["description_uz"] = p.description_uz
    data["description_ru"] = p.description_ru
    data["step"] = str(p.step)
    data["min_qty"] = str(p.min_qty)
    data["max_qty"] = str(p.max_qty) if p.max_qty is not None else None
    data["images"] = [
        {
            "id": img.id,
            "image": img.image,
            "sort_order": img.sort_order,
            "is_primary": img.is_primary,
        }
        for img in p.images.all()
    ]
    if hasattr(p, "_current_discounts"):
        data["discounts"] = [
            {
                "id": d["id"],
                "name": d["name_uz"],
                "type": d["type"],
                "value": str(d["value"]),
                "max_discount": str(d["max_discount"]) if d["max_discount"] else None,
            }
            for d in p._current_discounts
        ]
    return data


@csrf_exempt
@require_GET
@require_permission(P.VIEW_PRODUCTS)
def list_products_view(request):
    svc = container.resolve(ProductService)
    result = svc.get_all(
        query=request.GET.get("q"),
        category_id=int(request.GET["category_id"]) if request.GET.get("category_id") else None,
        is_active=_parse_bool(request.GET.get("is_active")),
        in_stock=_parse_bool(request.GET.get("in_stock")),
        is_featured=_parse_bool(request.GET.get("is_featured")),
        unit=request.GET.get("unit"),
        min_price=_parse_decimal(request.GET.get("min_price")),
        max_price=_parse_decimal(request.GET.get("max_price")),
        has_discount=_parse_bool(request.GET.get("has_discount")),
        stock_status=request.GET.get("stock_status"),
        has_sku=_parse_bool(request.GET.get("has_sku")),
        has_barcode=_parse_bool(request.GET.get("has_barcode")),
        order_by=request.GET.get("order_by", "-created_at"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
    )
    result["items"] = [_serialize_product(p) for p in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_PRODUCTS)
def get_product_view(request, product_id):
    svc = container.resolve(ProductService)
    product = svc.get_by_id(product_id)
    if not product:
        return not_found("Product not found")
    return success(data=_serialize_product_detail(product))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def create_product_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["category_id", "name_uz", "unit", "price"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateProductDTO(
        category_id=int(data["category_id"]),
        name_uz=data["name_uz"],
        unit=data["unit"],
        price=str(data["price"]),
        name_ru=data.get("name_ru", ""),
        description_uz=data.get("description_uz", ""),
        description_ru=data.get("description_ru", ""),
        sku=data.get("sku"),
        barcode=data.get("barcode"),
        cost_price=str(data["cost_price"]) if data.get("cost_price") is not None else None,
        step=str(data.get("step", "1")),
        min_qty=str(data.get("min_qty", "1")),
        max_qty=str(data["max_qty"]) if data.get("max_qty") is not None else None,
        in_stock=data.get("in_stock", True),
        stock_qty=str(data["stock_qty"]) if data.get("stock_qty") is not None else None,
        low_stock_threshold=str(data["low_stock_threshold"]) if data.get("low_stock_threshold") is not None else None,
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
        is_featured=data.get("is_featured", False),
        images=data.get("images", []),
    )
    svc = container.resolve(ProductService)
    result = svc.create_product(dto)
    return created(data=result, message="Product created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_PRODUCTS)
def update_product_view(request, product_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateProductDTO(**{k: v for k, v in data.items() if hasattr(UpdateProductDTO, k)})
    svc = container.resolve(ProductService)
    result = svc.update_product(product_id, dto)
    return success(data=result, message="Product updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_PRODUCTS)
def delete_product_view(request, product_id):
    svc = container.resolve(ProductService)
    result = svc.delete_product(product_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def restore_product_view(request, product_id):
    svc = container.resolve(ProductService)
    result = svc.restore_product(product_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def reorder_products_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error("ids must be a list of integers", status=422)

    svc = container.resolve(ProductService)
    result = svc.reorder(ids)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def activate_product_view(request, product_id):
    svc = container.resolve(ProductService)
    return success(data=svc.activate(product_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def deactivate_product_view(request, product_id):
    svc = container.resolve(ProductService)
    return success(data=svc.deactivate(product_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def feature_product_view(request, product_id):
    svc = container.resolve(ProductService)
    return success(data=svc.feature(product_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def unfeature_product_view(request, product_id):
    svc = container.resolve(ProductService)
    return success(data=svc.unfeature(product_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def update_stock_view(request, product_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    svc = container.resolve(ProductService)
    result = svc.update_stock(
        product_id,
        stock_qty=data.get("stock_qty"),
        in_stock=data.get("in_stock"),
    )
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def add_images_view(request, product_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    images = data.get("images")
    if not isinstance(images, list) or not images:
        return error("images must be a non-empty list", status=422)

    for img in images:
        if not isinstance(img, dict) or not img.get("image"):
            return error("Each image must have an 'image' field", status=422)

    svc = container.resolve(ProductService)
    result = svc.add_images(product_id, images)
    return created(data=result, message="Images added")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_PRODUCTS)
def remove_image_view(request, product_id, image_id):
    svc = container.resolve(ProductService)
    result = svc.remove_image(product_id, image_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def reorder_images_view(request, product_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error("ids must be a list of integers", status=422)

    svc = container.resolve(ProductService)
    result = svc.reorder_images(product_id, ids)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def set_primary_image_view(request, product_id, image_id):
    svc = container.resolve(ProductService)
    result = svc.set_primary_image(product_id, image_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def assign_discounts_view(request, product_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    discount_ids = data.get("discount_ids")
    if not isinstance(discount_ids, list) or not all(isinstance(i, int) for i in discount_ids):
        return error("discount_ids must be a list of integers", status=422)

    svc = container.resolve(ProductService)
    result = svc.assign_discounts(product_id, discount_ids)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PRODUCTS)
def remove_discounts_view(request, product_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    discount_ids = data.get("discount_ids")
    if not isinstance(discount_ids, list) or not all(isinstance(i, int) for i in discount_ids):
        return error("discount_ids must be a list of integers", status=422)

    svc = container.resolve(ProductService)
    result = svc.remove_discounts(product_id, discount_ids)
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def product_stats_view(request):
    svc = container.resolve(ProductService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    cat_raw = request.GET.get("category_id")
    category_id = int(cat_raw) if cat_raw else None
    return success(data=svc.stats(date_from=date_from, date_to=date_to, category_id=category_id))
