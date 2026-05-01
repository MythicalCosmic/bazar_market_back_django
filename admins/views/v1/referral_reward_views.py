import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.referral_reward import CreateReferralRewardDTO, UpdateReferralRewardDTO
from admins.services.v1.referral_reward_service import ReferralRewardService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found


def _serialize_reward(r) -> dict:
    data = {
        "id": r.id,
        "name": r.name,
        "type": r.type,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat(),
    }
    if r.type == "coupon":
        data["coupon_type"] = r.coupon_type
        data["coupon_value"] = str(r.coupon_value) if r.coupon_value is not None else None
        data["coupon_max_discount"] = str(r.coupon_max_discount) if r.coupon_max_discount is not None else None
        data["coupon_min_order"] = str(r.coupon_min_order) if r.coupon_min_order is not None else None
        data["coupon_expires_days"] = r.coupon_expires_days
    elif r.type == "free_delivery":
        data["free_delivery_count"] = r.free_delivery_count
    elif r.type == "bonus_product":
        data["bonus_product_id"] = r.bonus_product_id
        data["bonus_product_name"] = r.bonus_product.name_uz if r.bonus_product else None
        data["bonus_quantity"] = str(r.bonus_quantity)
    return data


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def list_referral_rewards_view(request):
    svc = container.resolve(ReferralRewardService)
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_reward(r) for r in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def get_referral_reward_view(request, reward_id):
    svc = container.resolve(ReferralRewardService)
    reward = svc.get_by_id(reward_id)
    if not reward:
        return not_found("Referral reward not found")
    return success(data=_serialize_reward(reward))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def create_referral_reward_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["name", "type"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateReferralRewardDTO(
        name=data["name"],
        type=data["type"],
        coupon_type=data.get("coupon_type", "percent"),
        coupon_value=str(data["coupon_value"]) if data.get("coupon_value") is not None else None,
        coupon_max_discount=str(data["coupon_max_discount"]) if data.get("coupon_max_discount") is not None else None,
        coupon_min_order=str(data["coupon_min_order"]) if data.get("coupon_min_order") is not None else None,
        coupon_expires_days=data.get("coupon_expires_days", 30),
        free_delivery_count=data.get("free_delivery_count", 1),
        bonus_product_id=data.get("bonus_product_id"),
        bonus_quantity=str(data.get("bonus_quantity", "1")),
        is_active=data.get("is_active", False),
    )
    svc = container.resolve(ReferralRewardService)
    result = svc.create_reward(dto)
    return created(data=result, message="Referral reward created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def update_referral_reward_view(request, reward_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateReferralRewardDTO(**{k: v for k, v in data.items() if hasattr(UpdateReferralRewardDTO, k)})
    svc = container.resolve(ReferralRewardService)
    result = svc.update_reward(reward_id, dto)
    return success(data=result, message="Referral reward updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def delete_referral_reward_view(request, reward_id):
    svc = container.resolve(ReferralRewardService)
    return success(data=svc.delete_reward(reward_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def activate_referral_reward_view(request, reward_id):
    svc = container.resolve(ReferralRewardService)
    return success(data=svc.activate(reward_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REFERRAL_REWARDS)
def deactivate_referral_reward_view(request, reward_id):
    svc = container.resolve(ReferralRewardService)
    return success(data=svc.deactivate(reward_id))
