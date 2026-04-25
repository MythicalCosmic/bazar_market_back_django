from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from admins.services.v1.address_service import AddressService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, not_found


def _serialize_address(a) -> dict:
    data = {
        "id": a.id,
        "label": a.label,
        "address_text": a.address_text,
        "latitude": str(a.latitude),
        "longitude": str(a.longitude),
        "entrance": a.entrance,
        "floor": a.floor,
        "apartment": a.apartment,
        "comment": a.comment,
        "is_default": a.is_default,
        "is_active": a.is_active,
        "created_at": a.created_at.isoformat(),
    }
    if hasattr(a, "user") and a.user:
        data["user"] = {
            "id": a.user.id,
            "first_name": a.user.first_name,
            "last_name": a.user.last_name,
            "phone": a.user.phone,
        }
    else:
        data["user_id"] = a.user_id
    return data


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def list_addresses_view(request):
    svc = container.resolve(AddressService)
    is_active_raw = request.GET.get("is_active")
    is_active = {"true": True, "false": False}.get(is_active_raw.lower()) if is_active_raw else None
    user_raw = request.GET.get("user_id")
    user_id = int(user_raw) if user_raw else None
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        user_id=user_id,
        is_active=is_active,
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_address(a) for a in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def user_addresses_view(request, user_id):
    svc = container.resolve(AddressService)
    addresses = svc.get_by_user(user_id)
    return success(data=[_serialize_address(a) for a in addresses])


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def get_address_view(request, address_id):
    svc = container.resolve(AddressService)
    address = svc.get_by_id(address_id)
    if not address:
        return not_found("Address not found")
    return success(data=_serialize_address(address))
