import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from base.container import container
from base.responses import success, error
from base.permissions import require_auth
from customer.services.v1.referral_service import CustomerReferralService


@csrf_exempt
@require_GET
@require_auth
def my_referral_view(request):
    svc = container.resolve(CustomerReferralService)
    return success(data=svc.get_my_referral(request.user_obj))


@csrf_exempt
@require_GET
@require_auth
def my_referrals_list_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CustomerReferralService)
    result = svc.list_my_referrals(request.user_obj.id, page=page, per_page=per_page)
    result["items"] = [
        {
            "id": r.id,
            "referred_name": r.referred.first_name,
            "reward_amount": str(r.reward_amount),
            "is_rewarded": r.is_rewarded,
            "created_at": r.created_at.isoformat(),
        }
        for r in result["items"]
    ]
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def apply_referral_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    code = (data.get("referral_code") or "").strip()
    if not code:
        return error("referral_code is required", status=422)

    svc = container.resolve(CustomerReferralService)
    result = svc.apply_referral(request.user_obj.id, code)
    return success(data=result)
