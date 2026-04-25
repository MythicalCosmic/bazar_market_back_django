from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from base.container import container
from base.responses import success, not_found, error
from customer.services.v1.catalog_service import CatalogService


def _serialize_product(p) -> dict:
    data = {
        "id": p.id,
        "uuid": str(p.uuid),
        "name_uz": p.name_uz,
        "name_ru": p.name_ru,
        "price": str(p.price),
        "unit": p.unit,
        "in_stock": p.in_stock,
        "is_featured": p.is_featured,
        "category_id": p.category_id,
    }
    if hasattr(p, "category") and p.category:
        data["category_name"] = p.category.name_uz
    if hasattr(p, "primary_image"):
        data["image"] = p.primary_image
    if hasattr(p, "_discounted_price"):
        data["discounted_price"] = str(p._discounted_price)
    if hasattr(p, "total_sold") and p.total_sold:
        data["total_sold"] = str(p.total_sold)
    return data


def _serialize_product_detail(p) -> dict:
    from decimal import Decimal
    data = _serialize_product(p)
    data.update({
        "description_uz": p.description_uz,
        "description_ru": p.description_ru,
        "step": str(p.step),
        "min_qty": str(p.min_qty),
        "max_qty": str(p.max_qty) if p.max_qty else None,
        "stock_qty": str(p.stock_qty) if p.stock_qty is not None else None,
        "sku": p.sku,
        "images": [
            {"id": img.id, "image": img.image, "is_primary": img.is_primary}
            for img in p.images.all()
        ],
    })

    if hasattr(p, "_current_discounts"):
        discounts = p._current_discounts
        data["discounts"] = [
            {
                "id": d["id"],
                "name": d["name_uz"],
                "type": d["type"],
                "value": str(d["value"]),
            }
            for d in discounts
        ]
        # Calculate best discounted price
        best_price = p.price
        for d in discounts:
            if d["type"] == "percent":
                disc = p.price * d["value"] / 100
                if d["max_discount"]:
                    disc = min(disc, d["max_discount"])
            else:
                disc = min(d["value"], p.price)
            candidate = p.price - disc
            if candidate < best_price:
                best_price = candidate
        if best_price < p.price:
            data["discounted_price"] = str(max(best_price, Decimal(0)))

    return data


def _serialize_category(c) -> dict:
    data = {
        "id": c.id,
        "name_uz": c.name_uz,
        "name_ru": c.name_ru,
        "image": c.image,
    }
    if hasattr(c, "product_count"):
        data["product_count"] = c.product_count
    return data


@csrf_exempt
@require_GET
def list_products_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    category_id = request.GET.get("category_id")
    if category_id:
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            return error("Invalid category_id", status=422)

    svc = container.resolve(CatalogService)
    result = svc.list_products(
        category_id=category_id,
        query=request.GET.get("q"),
        is_featured=request.GET.get("is_featured") == "true" if request.GET.get("is_featured") else None,
        order_by=request.GET.get("order_by", "sort_order"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_product(p) for p in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
def get_product_view(request, product_id):
    svc = container.resolve(CatalogService)
    product = svc.get_product(product_id)
    if not product:
        return not_found("Product not found")
    return success(data=_serialize_product_detail(product))


@csrf_exempt
@require_GET
def list_categories_view(request):
    svc = container.resolve(CatalogService)
    categories = svc.list_categories()
    return success(data=[_serialize_category(c) for c in categories])


@csrf_exempt
@require_GET
def category_tree_view(request):
    svc = container.resolve(CatalogService)
    return success(data=svc.get_category_tree())


@csrf_exempt
@require_GET
def featured_products_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CatalogService)
    result = svc.get_featured(page=page, per_page=per_page)
    result["items"] = [_serialize_product(p) for p in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
def popular_products_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CatalogService)
    result = svc.popular_products(page=page, per_page=per_page)
    result["items"] = [_serialize_product(p) for p in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
def search_products_view(request):
    query = request.GET.get("q", "").strip()
    if not query:
        return error("Search query is required", status=422)

    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CatalogService)
    result = svc.search(query=query, page=page, per_page=per_page)
    result["items"] = [_serialize_product(p) for p in result["items"]]
    return success(data=result)
