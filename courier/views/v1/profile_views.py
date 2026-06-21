import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from base.container import container
from base.responses import success, error
from base.permissions import require_role

from courier.services.v1.courier_service import CourierService
from courier.serializers import courier_me

require_courier = require_role("courier")


@csrf_exempt
@require_GET
@require_courier
def me_view(request):
    svc = container.resolve(CourierService)
    profile = svc.get_profile(request.user_obj)
    return success(data=courier_me(request.user_obj, profile))


@csrf_exempt
@require_http_methods(["PATCH", "POST"])
@require_courier
def online_view(request):
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")
    if "online" not in data:
        return error("online is required", status=422)
    svc = container.resolve(CourierService)
    profile = svc.set_online(request.user_obj, bool(data.get("online")))
    return success(data={"online": profile.is_online})


@csrf_exempt
@require_http_methods(["PATCH", "POST"])
@require_courier
def prefs_view(request):
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")
    svc = container.resolve(CourierService)
    profile = svc.update_prefs(request.user_obj, data)
    return success(data=courier_me(request.user_obj, profile)["prefs"])
