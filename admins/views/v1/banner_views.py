import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.banner import CreateBannerDTO, UpdateBannerDTO
from admins.services.v1.banner_service import BannerService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _serialize_banner(b) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "image": b.image,
        "link_type": b.link_type,
        "link_value": b.link_value,
        "sort_order": b.sort_order,
        "starts_at": b.starts_at.isoformat() if b.starts_at else None,
        "expires_at": b.expires_at.isoformat() if b.expires_at else None,
        "is_active": b.is_active,
        "created_at": b.created_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_BANNERS)
def list_banners_view(request):
    svc = container.resolve(BannerService)
    result = svc.get_all(
        is_active=_parse_bool(request.GET.get("is_active")),
        scheduled=request.GET.get("scheduled"),
        order_by=request.GET.get("order_by", "sort_order"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
    )
    result["items"] = [_serialize_banner(b) for b in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_BANNERS)
def get_banner_view(request, banner_id):
    svc = container.resolve(BannerService)
    banner = svc.get_by_id(banner_id)
    if not banner:
        return not_found("Banner not found")
    return success(data=_serialize_banner(banner))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_BANNERS)
def create_banner_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    if not data.get("image"):
        return error("image is required", status=422)

    dto = CreateBannerDTO(
        image=data["image"],
        title=data.get("title", ""),
        link_type=data.get("link_type", "none"),
        link_value=data.get("link_value", ""),
        sort_order=data.get("sort_order", 0),
        starts_at=data.get("starts_at"),
        expires_at=data.get("expires_at"),
        is_active=data.get("is_active", True),
    )
    svc = container.resolve(BannerService)
    result = svc.create_banner(dto)
    return created(data=result, message="Banner created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_BANNERS)
def update_banner_view(request, banner_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateBannerDTO(**{k: v for k, v in data.items() if hasattr(UpdateBannerDTO, k)})
    svc = container.resolve(BannerService)
    result = svc.update_banner(banner_id, dto)
    return success(data=result, message="Banner updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_BANNERS)
def delete_banner_view(request, banner_id):
    svc = container.resolve(BannerService)
    return success(data=svc.delete_banner(banner_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_BANNERS)
def reorder_banners_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error("ids must be a list of integers", status=422)

    svc = container.resolve(BannerService)
    return success(data=svc.reorder(ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_BANNERS)
def activate_banner_view(request, banner_id):
    svc = container.resolve(BannerService)
    return success(data=svc.activate(banner_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_BANNERS)
def deactivate_banner_view(request, banner_id):
    svc = container.resolve(BannerService)
    return success(data=svc.deactivate(banner_id))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def banner_stats_view(request):
    svc = container.resolve(BannerService)
    return success(data=svc.stats())
