import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from base.container import container
from base.responses import success, error
from base.permissions import require_role

from courier.services.v1.courier_service import CourierService

require_courier = require_role("courier")


@csrf_exempt
@require_POST
@require_courier
def register_device_view(request):
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")
    svc = container.resolve(CourierService)
    svc.register_device(request.user_obj, data.get("token"), data.get("platform", ""))
    return success(message="Device registered")


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
@require_courier
def unregister_device_view(request, token):
    # Prefer a body token when supplied (keeps the token out of access logs and
    # sidesteps any path-encoding issues); fall back to the path param.
    if request.body:
        try:
            body_token = (json.loads(request.body) or {}).get("token")
            if body_token:
                token = body_token
        except (json.JSONDecodeError, ValueError):
            pass
    if not token:
        return error("token is required", status=422)
    svc = container.resolve(CourierService)
    svc.unregister_device(request.user_obj, token)
    return success(message="Device unregistered")
