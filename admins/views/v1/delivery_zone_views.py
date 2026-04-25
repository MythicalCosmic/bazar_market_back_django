import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.delivery_zone import CreateDeliveryZoneDTO, UpdateDeliveryZoneDTO
from admins.services.v1.delivery_zone_service import DeliveryZoneService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, created, not_found


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _serialize_zone(z) -> dict:
    return {
        "id": z.id,
        "name": z.name,
        "polygon": z.polygon,
        "delivery_fee": str(z.delivery_fee),
        "min_order": str(z.min_order),
        "estimated_minutes": z.estimated_minutes,
        "is_active": z.is_active,
        "sort_order": z.sort_order,
        "created_at": z.created_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_permission(P.VIEW_DELIVERY_ZONES)
def list_zones_view(request):
    svc = container.resolve(DeliveryZoneService)
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        is_active=_parse_bool(request.GET.get("is_active")),
        order_by=request.GET.get("order_by", "sort_order"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_zone(z) for z in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_DELIVERY_ZONES)
def get_zone_view(request, zone_id):
    svc = container.resolve(DeliveryZoneService)
    zone = svc.get_by_id(zone_id)
    if not zone:
        return not_found("Delivery zone not found")
    return success(data=_serialize_zone(zone))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DELIVERY_ZONES)
def create_zone_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["name", "polygon", "delivery_fee"]
    missing = [f for f in required if f not in data]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateDeliveryZoneDTO(
        name=data["name"],
        polygon=data["polygon"],
        delivery_fee=str(data["delivery_fee"]),
        min_order=str(data.get("min_order", "0")),
        estimated_minutes=data.get("estimated_minutes"),
        is_active=data.get("is_active", True),
        sort_order=data.get("sort_order", 0),
    )
    svc = container.resolve(DeliveryZoneService)
    result = svc.create_zone(dto)
    return created(data=result, message="Delivery zone created")


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_DELIVERY_ZONES)
def update_zone_view(request, zone_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateDeliveryZoneDTO(**{k: v for k, v in data.items() if hasattr(UpdateDeliveryZoneDTO, k)})
    svc = container.resolve(DeliveryZoneService)
    result = svc.update_zone(zone_id, dto)
    return success(data=result, message="Zone updated")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_DELIVERY_ZONES)
def delete_zone_view(request, zone_id):
    svc = container.resolve(DeliveryZoneService)
    return success(data=svc.delete_zone(zone_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DELIVERY_ZONES)
def reorder_zones_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ids = data.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        return error("ids must be a list of integers", status=422)

    svc = container.resolve(DeliveryZoneService)
    return success(data=svc.reorder(ids))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DELIVERY_ZONES)
def activate_zone_view(request, zone_id):
    svc = container.resolve(DeliveryZoneService)
    return success(data=svc.activate(zone_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_DELIVERY_ZONES)
def deactivate_zone_view(request, zone_id):
    svc = container.resolve(DeliveryZoneService)
    return success(data=svc.deactivate(zone_id))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def zone_stats_view(request):
    svc = container.resolve(DeliveryZoneService)
    return success(data=svc.stats())
