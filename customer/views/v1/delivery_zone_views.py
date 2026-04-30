from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from base.container import container
from base.ratelimit import ratelimit
from base.responses import success, error
from customer.services.v1.delivery_zone_service import CustomerDeliveryZoneService


@csrf_exempt
@require_GET
@ratelimit(30, per=60)
def check_delivery_view(request):
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")

    if not lat or not lng:
        return error("lat and lng are required", status=422)

    try:
        lat_dec = Decimal(lat)
        lng_dec = Decimal(lng)
    except (InvalidOperation, ValueError):
        return error("Invalid lat or lng", status=422)

    svc = container.resolve(CustomerDeliveryZoneService)
    result = svc.check_delivery(lat_dec, lng_dec)
    return success(data=result)


@csrf_exempt
@require_GET
@ratelimit(60, per=60)
def delivery_info_view(request):
    from base.models import DeliveryZone, Setting

    zones = DeliveryZone.objects.filter(is_active=True).order_by("sort_order")
    zone_list = [
        {
            "id": z.id,
            "name": z.name,
            "delivery_fee": str(z.delivery_fee),
            "min_order": str(z.min_order),
            "estimated_minutes": z.estimated_minutes,
        }
        for z in zones
    ]

    default_fee = Setting.objects.filter(pk="default_delivery_fee").first()
    min_order = Setting.objects.filter(pk="min_order_total").first()

    return success(data={
        "default_delivery_fee": default_fee.value if default_fee else "0",
        "min_order_total": min_order.value if min_order else "0",
        "zones": zone_list,
    })
