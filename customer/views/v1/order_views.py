import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from base.container import container
from base.responses import success, error, created, not_found
from base.permissions import require_auth
from base.ratelimit import ratelimit
from customer.dto.order import PlaceOrderDTO
from customer.services.v1.order_service import CustomerOrderService


def _serialize_order(o) -> dict:
    return {
        "id": o.id,
        "uuid": str(o.uuid),
        "order_number": o.order_number,
        "status": o.status,
        "subtotal": str(o.subtotal),
        "delivery_fee": str(o.delivery_fee),
        "discount": str(o.discount),
        "total": str(o.total),
        "payment_method": o.payment_method,
        "payment_status": o.payment_status,
        "delivery_address_text": o.delivery_address_text,
        "user_note": o.user_note,
        "scheduled_time": o.scheduled_time.isoformat() if o.scheduled_time else None,
        "created_at": o.created_at.isoformat(),
        "confirmed_at": o.confirmed_at.isoformat() if o.confirmed_at else None,
        "preparing_at": o.preparing_at.isoformat() if o.preparing_at else None,
        "delivering_at": o.delivering_at.isoformat() if o.delivering_at else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        "cancelled_at": o.cancelled_at.isoformat() if o.cancelled_at else None,
    }


def _serialize_order_detail(o) -> dict:
    data = _serialize_order(o)

    if hasattr(o, "_items"):
        data["items"] = [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "unit": item.unit,
                "unit_price": str(item.unit_price),
                "quantity": str(item.quantity),
                "total": str(item.total),
            }
            for item in o._items
        ]

    if hasattr(o, "_status_log"):
        data["status_log"] = [
            {
                "from_status": log.from_status,
                "to_status": log.to_status,
                "note": log.note,
                "created_at": log.created_at.isoformat(),
            }
            for log in o._status_log
        ]

    return data


@csrf_exempt
@require_POST
@require_auth
@ratelimit(10, per=60)
def place_order_view(request):
    if not request.user_obj.is_phone_verified:
        return error("Phone verification required before placing orders", status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    address_id = data.get("address_id")
    payment_method = data.get("payment_method")

    if not address_id or not payment_method:
        return error("address_id and payment_method are required", status=422)

    dto = PlaceOrderDTO(
        address_id=int(address_id),
        payment_method=payment_method,
        coupon_code=data.get("coupon_code"),
        user_note=data.get("user_note", ""),
        scheduled_time=data.get("scheduled_time"),
    )

    svc = container.resolve(CustomerOrderService)
    result = svc.place_order(request.user_obj.id, dto)
    return created(data=result, message="Order placed successfully")


@csrf_exempt
@require_GET
@require_auth
def list_orders_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CustomerOrderService)
    result = svc.list_orders(
        request.user_obj.id,
        status=request.GET.get("status"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_order(o) for o in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_auth
def get_order_view(request, order_id):
    svc = container.resolve(CustomerOrderService)
    order = svc.get_order(request.user_obj.id, order_id)
    if not order:
        return not_found("Order not found")
    return success(data=_serialize_order_detail(order))


@csrf_exempt
@require_GET
@require_auth
def active_orders_view(request):
    svc = container.resolve(CustomerOrderService)
    orders = svc.active_orders(request.user_obj.id)
    return success(data=[_serialize_order(o) for o in orders])


@csrf_exempt
@require_POST
@require_auth
def cancel_order_view(request, order_id):
    reason = ""
    if request.body:
        try:
            data = json.loads(request.body)
            reason = data.get("reason", "")
        except (json.JSONDecodeError, ValueError):
            pass

    svc = container.resolve(CustomerOrderService)
    result = svc.cancel_order(request.user_obj.id, order_id, reason)
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def reorder_view(request, order_id):
    svc = container.resolve(CustomerOrderService)
    result = svc.reorder(request.user_obj.id, order_id)
    return success(data=result)
