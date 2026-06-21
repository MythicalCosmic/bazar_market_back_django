import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from base.container import container
from base.responses import success, error, not_found
from base.permissions import require_role

from courier.services.v1.courier_service import CourierService
from courier.serializers import active_order, history_order

require_courier = require_role("courier")


@csrf_exempt
@require_GET
@require_courier
def active_orders_view(request):
    svc = container.resolve(CourierService)
    orders, states, origin = svc.active_orders(request.user_obj)
    data = [active_order(o, states.get(o.id), origin) for o in orders]
    return success(data={"orders": data})


@csrf_exempt
@require_GET
@require_courier
def order_detail_view(request, ref):
    svc = container.resolve(CourierService)
    order, state, origin = svc.get_order(request.user_obj, ref)
    if not order:
        return not_found("Order not found")
    return success(data=active_order(order, state, origin))


@csrf_exempt
@require_http_methods(["PATCH", "POST"])
@require_courier
def update_status_view(request, ref):
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")
    target = data.get("status")
    if not target:
        return error("status is required", status=422)
    svc = container.resolve(CourierService)
    order, state, now = svc.advance_status(request.user_obj, ref, target)
    return success(data={"id": order.order_number, "status": state.status, "updatedAt": now.isoformat()})


@csrf_exempt
@require_POST
@require_courier
def advance_status_view(request, ref):
    """Convenience: bump to the next status server-side (no body)."""
    svc = container.resolve(CourierService)
    order, state, now = svc.advance_next(request.user_obj, ref)
    return success(data={"id": order.order_number, "status": state.status, "updatedAt": now.isoformat()})


@csrf_exempt
@require_GET
@require_courier
def history_view(request):
    try:
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("pageSize", request.GET.get("page_size", 20)))
    except (ValueError, TypeError):
        return error("page and pageSize must be integers", status=422)
    svc = container.resolve(CourierService)
    result = svc.history(
        request.user_obj,
        period=request.GET.get("period", "today"),
        status=request.GET.get("status", "all"),
        q=request.GET.get("q", ""),
        page=page,
        page_size=page_size,
    )
    result["orders"] = [history_order(o) for o in result["orders"]]
    return success(data=result)
