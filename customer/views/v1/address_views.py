import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from base.container import container
from base.responses import success, error, created
from base.permissions import require_auth
from customer.dto.address import CreateAddressDTO, UpdateAddressDTO
from customer.services.v1.address_service import CustomerAddressService


def _serialize_address(a) -> dict:
    return {
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
    }


@csrf_exempt
@require_GET
@require_auth
def list_addresses_view(request):
    svc = container.resolve(CustomerAddressService)
    addresses = svc.list_addresses(request.user_obj.id)
    return success(data=[_serialize_address(a) for a in addresses])


@csrf_exempt
@require_POST
@require_auth
def add_address_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["latitude", "longitude", "address_text"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateAddressDTO(
        latitude=str(data["latitude"]),
        longitude=str(data["longitude"]),
        address_text=data["address_text"],
        label=data.get("label", ""),
        entrance=data.get("entrance", ""),
        floor=data.get("floor", ""),
        apartment=data.get("apartment", ""),
        comment=data.get("comment", ""),
        is_default=data.get("is_default", False),
    )
    svc = container.resolve(CustomerAddressService)
    result = svc.add_address(request.user_obj.id, dto)
    return created(data=result, message="Address added")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth
def update_address_view(request, address_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateAddressDTO(**{k: v for k, v in data.items() if hasattr(UpdateAddressDTO, k)})
    svc = container.resolve(CustomerAddressService)
    result = svc.update_address(request.user_obj.id, address_id, dto)
    return success(data=result, message="Address updated")


@csrf_exempt
@require_POST
@require_auth
def delete_address_view(request, address_id):
    svc = container.resolve(CustomerAddressService)
    return success(data=svc.delete_address(request.user_obj.id, address_id))


@csrf_exempt
@require_POST
@require_auth
def set_default_address_view(request, address_id):
    svc = container.resolve(CustomerAddressService)
    return success(data=svc.set_default(request.user_obj.id, address_id))
