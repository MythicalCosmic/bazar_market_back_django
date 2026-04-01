from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from admins.services.v1.stats_service import StatsService
from base.permissions import require_permission, P
from base.responses import success


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def staff_stats_view(request):
    svc = StatsService()
    return success(data=svc.staff_stats())


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def customer_stats_view(request):
    svc = StatsService()
    ref_lat = request.GET.get("lat")
    ref_lng = request.GET.get("lng")
    lat = lng = None
    if ref_lat and ref_lng:
        try:
            lat = Decimal(ref_lat)
            lng = Decimal(ref_lng)
        except InvalidOperation:
            pass
    return success(data=svc.customer_stats(reference_lat=lat, reference_lng=lng))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def overview_view(request):
    svc = StatsService()
    return success(data=svc.overview())
