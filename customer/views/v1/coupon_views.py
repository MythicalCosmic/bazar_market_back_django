import json
from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from base.container import container
from base.responses import success, error
from base.permissions import require_auth
from customer.services.v1.coupon_service import CustomerCouponService


@csrf_exempt
@require_POST
@require_auth
def validate_coupon_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    code = data.get("code")
    subtotal = data.get("subtotal")
    if not code or subtotal is None:
        return error("code and subtotal are required", status=422)

    try:
        subtotal_dec = Decimal(str(subtotal))
    except (InvalidOperation, ValueError):
        return error("Invalid subtotal", status=422)

    svc = container.resolve(CustomerCouponService)
    result = svc.validate_coupon(request.user_obj.id, code, subtotal_dec)
    return success(data=result)
