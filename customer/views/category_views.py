import json
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from customer.services.category_service import CategoryService
from base.container import container
from base.responses import success, error, created, not_found


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except(ValueError, TypeError):
        return None
    
def _serialize_category(c) -> dict:
    return {
        "id": c.id,
        "name_uz": c.name_uz,
        "name_ru": c.name_ru,
        "image": c.image,
        "parent_id": c.parent_id,
        "sort_order": c.sort_order,
        "is_active": c.is_active,
        "created_at": c.created_at
    }

@csrf_exempt
@require_GET
def list_categories_view(request):
    svc = container.resolve(CategoryService)
    is_active_raw = request.GET.get("is_active")
    is_active = {"true": True, "false": False}.get(is_active_raw.lower()) if is_active_raw else None
    parent_raw = request.GET.get("parent_id")
    parent_id = int(parent_raw) if parent_raw is not None else None
    result = svc.get_all(
        query=request.GET.get("q"),
        is_active=is_active,
        parent_id=parent_id,
        order_by=request.GET.get("order_by", "sort_order"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
        is_deleted=bool(request.GET.get("is_deleted", None)),
    )
    result["items"] = [_serialize_category(c) for c in result["items"]]
    return success(data=result)

@csrf_exempt
@require_GET
def get_category_view(request, category_id):
    svc = container.resolve(CategoryService)
    category = svc.get_by_id(category_id)
    if not category:
        return not_found("Category not found")
    return success(data=_serialize_category(category_id))

@csrf_exempt
@require_GET
def category_tree_view(request):
    svc = container.resolve(CategoryService)
    return success(data=svc.get_tree())

