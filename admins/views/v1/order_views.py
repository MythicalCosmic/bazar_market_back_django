import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from admins.services.v1.order_service import OrderService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, not_found


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _parse_decimal(value):
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _serialize_user_brief(u):
    if not u:
        return None
    return {
        "id": u.id,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "phone": u.phone,
        "role": u.role,
    }


def _serialize_order(o) -> dict:
    data = {
        "id": o.id,
        "uuid": str(o.uuid),
        "order_number": o.order_number,
        "status": o.status,
        "total": str(o.total),
        "subtotal": str(o.subtotal),
        "delivery_fee": str(o.delivery_fee),
        "discount": str(o.discount),
        "payment_method": o.payment_method,
        "payment_status": o.payment_status,
        "delivery_address_text": o.delivery_address_text,
        "scheduled_time": o.scheduled_time.isoformat() if o.scheduled_time else None,
        "user_note": o.user_note,
        "admin_note": o.admin_note,
        "created_at": o.created_at.isoformat(),
        "confirmed_at": o.confirmed_at.isoformat() if o.confirmed_at else None,
        "preparing_at": o.preparing_at.isoformat() if o.preparing_at else None,
        "delivering_at": o.delivering_at.isoformat() if o.delivering_at else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
        "cancelled_at": o.cancelled_at.isoformat() if o.cancelled_at else None,
        "cancel_reason": o.cancel_reason,
    }
    if hasattr(o, "user") and o.user:
        data["user"] = _serialize_user_brief(o.user)
    else:
        data["user_id"] = o.user_id
    if hasattr(o, "assigned_courier"):
        data["courier"] = _serialize_user_brief(o.assigned_courier) if o.assigned_courier else None
    return data


def _serialize_order_detail(o) -> dict:
    data = _serialize_order(o)

    if hasattr(o, "address") and o.address:
        data["address"] = {
            "id": o.address.id,
            "label": o.address.label,
            "address_text": o.address.address_text,
            "latitude": str(o.address.latitude),
            "longitude": str(o.address.longitude),
        }

    if hasattr(o, "_items"):
        data["items"] = [
            {
                "id": item.id,
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
                "changed_by": log.changed_by.first_name if log.changed_by else None,
                "note": log.note,
                "created_at": log.created_at.isoformat(),
            }
            for log in o._status_log
        ]

    return data


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ORDERS)
def list_orders_view(request):
    svc = container.resolve(OrderService)
    user_raw = request.GET.get("user_id")
    courier_raw = request.GET.get("courier_id")
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        query=request.GET.get("q"),
        status=request.GET.get("status"),
        payment_status=request.GET.get("payment_status"),
        payment_method=request.GET.get("payment_method"),
        user_id=int(user_raw) if user_raw else None,
        courier_id=int(courier_raw) if courier_raw else None,
        has_courier=_parse_bool(request.GET.get("has_courier")),
        date_from=_parse_date(request.GET.get("date_from")),
        date_to=_parse_date(request.GET.get("date_to")),
        min_total=_parse_decimal(request.GET.get("min_total")),
        max_total=_parse_decimal(request.GET.get("max_total")),
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_order(o) for o in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ORDERS)
def get_order_view(request, order_id):
    svc = container.resolve(OrderService)
    order = svc.get_by_id(order_id)
    if not order:
        return not_found("Order not found")
    return success(data=_serialize_order_detail(order))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ORDERS)
def update_order_status_view(request, order_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    new_status = data.get("status")
    if not new_status:
        return error("status is required", status=422)

    svc = container.resolve(OrderService)
    result = svc.update_status(
        order_id,
        new_status=new_status,
        admin_user=request.user_obj,
        note=data.get("note", ""),
    )
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.ASSIGN_ORDERS)
def assign_courier_view(request, order_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    courier_id = data.get("courier_id")
    if not courier_id:
        return error("courier_id is required", status=422)

    svc = container.resolve(OrderService)
    result = svc.assign_courier(order_id, int(courier_id), admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.ASSIGN_ORDERS)
def unassign_courier_view(request, order_id):
    svc = container.resolve(OrderService)
    result = svc.unassign_courier(order_id, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PAYMENTS)
def update_payment_status_view(request, order_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    ps = data.get("payment_status")
    if not ps:
        return error("payment_status is required", status=422)

    svc = container.resolve(OrderService)
    result = svc.update_payment_status(order_id, ps, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ORDERS)
def add_admin_note_view(request, order_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    note = data.get("note", "").strip()
    if not note:
        return error("note is required", status=422)

    svc = container.resolve(OrderService)
    result = svc.add_admin_note(order_id, note)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ORDERS)
def cancel_order_view(request, order_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    svc = container.resolve(OrderService)
    result = svc.cancel(
        order_id,
        reason=data.get("reason", ""),
        admin_user=request.user_obj,
    )
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ORDERS)
def bulk_update_status_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    order_ids = data.get("order_ids")
    new_status = data.get("status")
    if not isinstance(order_ids, list) or not all(isinstance(i, int) for i in order_ids):
        return error("order_ids must be a list of integers", status=422)
    if not new_status:
        return error("status is required", status=422)

    svc = container.resolve(OrderService)
    result = svc.bulk_update_status(
        order_ids, new_status,
        admin_user=request.user_obj,
        note=data.get("note", ""),
    )
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def get_min_order_view(request):
    svc = container.resolve(OrderService)
    return success(data={"min_order_total": str(svc.get_min_order_total())})


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_SETTINGS)
def set_min_order_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    amount = data.get("amount")
    if amount is None:
        return error("amount is required", status=422)

    svc = container.resolve(OrderService)
    result = svc.set_min_order_total(amount)
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def order_stats_view(request):
    svc = container.resolve(OrderService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.stats(date_from=date_from, date_to=date_to))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ORDERS)
def accept_and_print_view(request, order_id):
    svc = container.resolve(OrderService)
    result = svc.update_status(
        order_id, new_status="confirmed",
        admin_user=request.user_obj, note="Accepted and printing",
    )
    from base.printing.print_queue import enqueue_print
    enqueue_print(order_id)
    result["printed"] = True
    return success(data=result, message="Order confirmed and sent to printer")


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_ORDERS)
def print_order_view(request, order_id):
    from base.models import Order
    if not Order.objects.filter(pk=order_id).exists():
        return not_found("Order not found")
    from base.printing.print_queue import enqueue_print
    enqueue_print(order_id)
    return success(message="Print job enqueued")
