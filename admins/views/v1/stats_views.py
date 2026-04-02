from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from admins.services.v1.stats_service import StatsService
from base.permissions import require_permission, P
from base.responses import success


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def staff_stats_view(request):
    svc = StatsService()
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.staff_stats(date_from=date_from, date_to=date_to))


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
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.customer_stats(
        reference_lat=lat, reference_lng=lng,
        date_from=date_from, date_to=date_to,
    ))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def overview_view(request):
    svc = StatsService()
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.overview(date_from=date_from, date_to=date_to))
