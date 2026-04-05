import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods

from admins.dto.user import CreateUserDTO, UpdateUserDTO
from admins.services.v1.user_service import UserService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found
import telescope


def _serialize_user(u) -> dict:
    return {
        "id": u.id,
        "uuid": str(u.uuid),
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "role": u.role,
        "language": u.language,
        "telegram_id": u.telegram_id,
        "is_active": u.is_active,
        "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
        "created_at": u.created_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def list_users_view(request):
    svc = container.resolve(UserService)
    is_active_raw = request.GET.get("is_active")
    is_active = {"true": True, "false": False}.get(is_active_raw.lower()) if is_active_raw else None
    result = svc.get_all(
        query=request.GET.get("q"),
        role=request.GET.get("role"),
        is_active=is_active,
        order_by=request.GET.get("order_by", "-created_at"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
        is_deleted=request.GET.get("is_deleted", False),
    )
    result["items"] = [_serialize_user(u) for u in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def get_user_view(request, user_id):
    svc = container.resolve(UserService)
    user = svc.get_by_id(user_id)
    if not user:
        return not_found("User not found")
    return success(data=_serialize_user(user))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_USERS)
def create_user_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["username", "first_name", "last_name", "role", "password"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateUserDTO(
        username=data["username"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        role=data["role"],
        password=data["password"],
        phone=data.get("phone"),
        language=data.get("language"),
        telegram_id=data.get("telegram_id"),
    )
    svc = container.resolve(UserService)
    result = svc.create_user(dto)
    return created(data=result, message="User created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_USERS)
def update_user_view(request, user_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateUserDTO(**{k: v for k, v in data.items() if hasattr(UpdateUserDTO, k)})
    svc = container.resolve(UserService)
    result = svc.update_user(user_id, dto)
    return success(data=result, message="User updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_USERS)
def delete_user_view(request, user_id):
    svc = container.resolve(UserService)
    result = svc.delete_user(user_id)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_USERS)
def restore_user_view(request, user_id):
    svc = container.resolve(UserService)
    result = svc.restore_user(user_id)
    return success(data=result)
