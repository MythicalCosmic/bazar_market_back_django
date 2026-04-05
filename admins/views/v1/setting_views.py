import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.setting import SetSettingDTO
from admins.services.v1.setting_service import SettingService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, not_found


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_SETTINGS)
def list_settings_view(request):
    svc = container.resolve(SettingService)
    return success(data=svc.get_all())


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_SETTINGS)
def get_setting_view(request, key):
    svc = container.resolve(SettingService)
    return success(data=svc.get_by_key(key))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_SETTINGS)
def set_setting_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    key = data.get("key")
    value = data.get("value")
    if not key or value is None:
        return error("key and value are required", status=422)

    dto = SetSettingDTO(
        key=key,
        value=value,
        type=data.get("type", "string"),
        description=data.get("description", ""),
    )
    svc = container.resolve(SettingService)
    result = svc.set_value(dto)
    return success(data=result)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_SETTINGS)
def delete_setting_view(request, key):
    svc = container.resolve(SettingService)
    return success(data=svc.delete(key))
