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
