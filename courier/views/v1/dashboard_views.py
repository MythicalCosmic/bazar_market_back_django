from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from base.container import container
from base.responses import success
from base.permissions import require_role

from courier.services.v1.courier_service import CourierService

require_courier = require_role("courier")


@csrf_exempt
@require_GET
@require_courier
def stats_view(request):
    svc = container.resolve(CourierService)
    date = request.GET.get("date", "today")
    return success(data=svc.dashboard_stats(request.user_obj, date))
