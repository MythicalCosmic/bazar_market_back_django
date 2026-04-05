import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.services.v1.role_service import RoleService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_ROLES)
def list_permissions_view(request):
    svc = container.resolve(RoleService)
    group = request.GET.get("group")
    return success(data=svc.list_permissions(group=group))


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_ROLES)
def list_permission_groups_view(request):
    svc = container.resolve(RoleService)
    return success(data=svc.list_permission_groups())


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_ROLES)
def get_role_permissions_view(request, role):
    svc = container.resolve(RoleService)
    return success(data=svc.get_role_permissions(role))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ROLES)
def set_role_permissions_view(request, role):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    codenames = data.get("permissions")
    if not isinstance(codenames, list) or not all(isinstance(c, str) for c in codenames):
        return error("permissions must be a list of strings", status=422)

    svc = container.resolve(RoleService)
    result = svc.set_role_permissions(role, codenames)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ROLES)
def reset_role_permissions_view(request, role):
    svc = container.resolve(RoleService)
    result = svc.reset_role_to_defaults(role)
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_ROLES)
def get_user_permissions_view(request, user_id):
    svc = container.resolve(RoleService)
    return success(data=svc.get_user_permissions(user_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ROLES)
def grant_user_permission_view(request, user_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    codename = data.get("permission")
    if not codename:
        return error("permission is required", status=422)

    svc = container.resolve(RoleService)
    result = svc.grant_user_permission(user_id, codename)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ROLES)
def deny_user_permission_view(request, user_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    codename = data.get("permission")
    if not codename:
        return error("permission is required", status=422)

    svc = container.resolve(RoleService)
    result = svc.deny_user_permission(user_id, codename)
    return success(data=result)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_ROLES)
def remove_user_permission_view(request, user_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    codename = data.get("permission")
    if not codename:
        return error("permission is required", status=422)

    svc = container.resolve(RoleService)
    result = svc.remove_user_permission(user_id, codename)
    return success(data=result)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_ROLES)
def clear_user_permissions_view(request, user_id):
    svc = container.resolve(RoleService)
    return success(data=svc.clear_user_permissions(user_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ROLES)
def sync_permissions_view(request):
    svc = container.resolve(RoleService)
    return success(data=svc.sync_all_permissions())
