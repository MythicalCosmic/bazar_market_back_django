import json
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.coupon import CreateCouponDTO, UpdateCouponDTO
from admins.services.v1.coupon_service import CouponService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _serialize_coupon(c) -> dict:
    data = {
        "id": c.id,
        "code": c.code,
        "type": c.type,
        "value": str(c.value),
        "min_order": str(c.min_order) if c.min_order is not None else None,
        "max_discount": str(c.max_discount) if c.max_discount is not None else None,
        "usage_limit": c.usage_limit,
        "per_user_limit": c.per_user_limit,
        "used_count": c.used_count,
        "starts_at": c.starts_at.isoformat() if c.starts_at else None,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat(),
    }
    if hasattr(c, "_usages"):
        data["recent_usages"] = [
            {
                "user_id": u.user_id,
                "user_name": f"{u.user.first_name} {u.user.last_name}" if u.user else None,
                "order_id": u.order_id,
                "discount_amount": str(u.discount_amount),
                "used_at": u.used_at.isoformat(),
            }
            for u in c._usages
        ]
    return data


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_COUPONS)
def list_coupons_view(request):
    svc = container.resolve(CouponService)
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        query=request.GET.get("q"),
        is_active=_parse_bool(request.GET.get("is_active")),
        type=request.GET.get("type"),
        valid_only=_parse_bool(request.GET.get("valid_only")) or False,
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_coupon(c) for c in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_COUPONS)
def get_coupon_view(request, coupon_id):
    svc = container.resolve(CouponService)
    coupon = svc.get_by_id(coupon_id)
    if not coupon:
        return not_found("Coupon not found")
    return success(data=_serialize_coupon(coupon))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_COUPONS)
def create_coupon_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["code", "type", "value"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateCouponDTO(
        code=data["code"],
        type=data["type"],
        value=str(data["value"]),
        min_order=str(data["min_order"]) if data.get("min_order") is not None else None,
        max_discount=str(data["max_discount"]) if data.get("max_discount") is not None else None,
        usage_limit=data.get("usage_limit"),
        per_user_limit=data.get("per_user_limit", 1),
        starts_at=data.get("starts_at"),
        expires_at=data.get("expires_at"),
        is_active=data.get("is_active", True),
    )
    svc = container.resolve(CouponService)
    result = svc.create_coupon(dto)
    return created(data=result, message="Coupon created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_COUPONS)
def update_coupon_view(request, coupon_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateCouponDTO(**{k: v for k, v in data.items() if hasattr(UpdateCouponDTO, k)})
    svc = container.resolve(CouponService)
    result = svc.update_coupon(coupon_id, dto)
    return success(data=result, message="Coupon updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_COUPONS)
def delete_coupon_view(request, coupon_id):
    svc = container.resolve(CouponService)
    return success(data=svc.delete_coupon(coupon_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_COUPONS)
def activate_coupon_view(request, coupon_id):
    svc = container.resolve(CouponService)
    return success(data=svc.activate(coupon_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_COUPONS)
def deactivate_coupon_view(request, coupon_id):
    svc = container.resolve(CouponService)
    return success(data=svc.deactivate(coupon_id))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def coupon_stats_view(request):
    svc = container.resolve(CouponService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.stats(date_from=date_from, date_to=date_to))
