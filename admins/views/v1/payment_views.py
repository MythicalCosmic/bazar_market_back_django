import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from admins.services.v1.payment_service import PaymentService
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


def _parse_decimal(value):
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _serialize_payment(p) -> dict:
    data = {
        "id": p.id,
        "uuid": str(p.uuid),
        "method": p.method,
        "external_id": p.external_id,
        "amount": str(p.amount),
        "status": p.status,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "created_at": p.created_at.isoformat(),
    }
    if hasattr(p, "order") and p.order:
        data["order"] = {
            "id": p.order.id,
            "order_number": p.order.order_number,
        }
        if hasattr(p.order, "user") and p.order.user:
            data["order"]["user"] = {
                "id": p.order.user.id,
                "first_name": p.order.user.first_name,
                "phone": p.order.user.phone,
            }
    else:
        data["order_id"] = p.order_id
    return data


def _serialize_payment_detail(p) -> dict:
    data = _serialize_payment(p)
    data["provider_data"] = p.provider_data
    return data


@csrf_exempt
@require_GET
@require_permission(P.VIEW_PAYMENTS)
def list_payments_view(request):
    svc = container.resolve(PaymentService)
    order_raw = request.GET.get("order_id")
    result = svc.get_all(
        query=request.GET.get("q"),
        status=request.GET.get("status"),
        method=request.GET.get("method"),
        order_id=int(order_raw) if order_raw else None,
        date_from=_parse_date(request.GET.get("date_from")),
        date_to=_parse_date(request.GET.get("date_to")),
        min_amount=_parse_decimal(request.GET.get("min_amount")),
        max_amount=_parse_decimal(request.GET.get("max_amount")),
        order_by=request.GET.get("order_by", "-created_at"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
    )
    result["items"] = [_serialize_payment(p) for p in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_PAYMENTS)
def get_payment_view(request, payment_id):
    svc = container.resolve(PaymentService)
    payment = svc.get_by_id(payment_id)
    if not payment:
        return not_found("Payment not found")
    return success(data=_serialize_payment_detail(payment))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_PAYMENTS)
def order_payments_view(request, order_id):
    svc = container.resolve(PaymentService)
    payments = svc.get_by_order(order_id)
    return success(data=[_serialize_payment(p) for p in payments])


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PAYMENTS)
def update_payment_status_view(request, payment_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    new_status = data.get("status")
    if not new_status:
        return error("status is required", status=422)

    svc = container.resolve(PaymentService)
    result = svc.update_status(payment_id, new_status)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_PAYMENTS)
def refund_payment_view(request, payment_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        data = {}

    svc = container.resolve(PaymentService)
    result = svc.refund(payment_id, reason=data.get("reason", ""))
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def payment_stats_view(request):
    svc = container.resolve(PaymentService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.stats(date_from=date_from, date_to=date_to))
