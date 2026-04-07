import json
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.category import CreateCategoryDTO, UpdateCategoryDTO
from admins.services.v1.category_service import CategoryService
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


def _serialize_category(c) -> dict:
    return {
        "id": c.id,
        "uuid": str(c.uuid),
        "name_uz": c.name_uz,
        "name_ru": c.name_ru,
        "image": c.image,
        "parent_id": c.parent_id,
        "sort_order": c.sort_order,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_permission(P.VIEW_CATEGORIES)
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
        is_deleted=bool(request.GET.get("is_deleted", None))
    )
    result["items"] = [_serialize_category(c) for c in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_CATEGORIES)
def get_category_view(request, category_id):
    svc = container.resolve(CategoryService)
    category = svc.get_by_id(category_id)
    if not category:
        return not_found("Category not found")
    return success(data=_serialize_category(category))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_CATEGORIES)
def category_tree_view(request):
    svc = container.resolve(CategoryService)
    return success(data=svc.get_tree())


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_CATEGORIES)
def create_category_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    if not data.get("name_uz"):
        return error("name_uz is required", status=422)

    dto = CreateCategoryDTO(
        name_uz=data["name_uz"],
        name_ru=data.get("name_ru", ""),
        image=data.get("image", ""),
        parent_id=data.get("parent_id"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
    )
    svc = container.resolve(CategoryService)
    result = svc.create_category(dto)
    return created(data=result, message="Category created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_CATEGORIES)
def update_category_view(request, category_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateCategoryDTO(**{k: v for k, v in data.items() if hasattr(UpdateCategoryDTO, k)})
    svc = container.resolve(CategoryService)
    result = svc.update_category(category_id, dto)
    return success(data=result, message="Category updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_CATEGORIES)
def delete_category_view(request, category_id):
    svc = container.resolve(CategoryService)
    result = svc.delete_category(category_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_CATEGORIES)
def restore_category_view(request, category_id):
    svc = container.resolve(CategoryService)
    result = svc.restore_category(category_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_CATEGORIES)
def reorder_categories_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error("ids must be a list of integers", status=422)

    svc = container.resolve(CategoryService)
    result = svc.reorder(ids)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_CATEGORIES)
def activate_category_view(request, category_id):
    svc = container.resolve(CategoryService)
    result = svc.activate(category_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_CATEGORIES)
def deactivate_category_view(request, category_id):
    svc = container.resolve(CategoryService)
    result = svc.deactivate(category_id)
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def category_stats_view(request):
    svc = container.resolve(CategoryService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.stats(date_from=date_from, date_to=date_to))
