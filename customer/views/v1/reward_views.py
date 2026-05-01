from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from base.models import UserReward
from base.permissions import require_auth
from base.responses import success


def _serialize_reward(r) -> dict:
    data = {
        "id": r.id,
        "type": r.type,
        "is_used": r.is_used,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "created_at": r.created_at.isoformat(),
    }
    if r.type == "coupon" and r.coupon:
        data["coupon_code"] = r.coupon.code
    elif r.type == "free_delivery":
        data["free_deliveries_remaining"] = r.free_deliveries_remaining
    elif r.type == "bonus_product":
        data["bonus_claimed"] = r.bonus_claimed
        data["bonus_quantity"] = str(r.bonus_quantity)
        if r.bonus_product:
            data["product_name"] = r.bonus_product.name_uz
            data["product_id"] = r.bonus_product_id
    return data


@csrf_exempt
@require_GET
@require_auth
def my_rewards_view(request):
    rewards = (
        UserReward.objects
        .filter(user_id=request.user_obj.id, is_used=False)
        .select_related("coupon", "bonus_product")
        .order_by("-created_at")
    )
    return success(data=[_serialize_reward(r) for r in rewards])
