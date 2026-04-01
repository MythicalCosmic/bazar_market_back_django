import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from admins.dto.customer import UpdateCustomerDTO
from admins.services.v1.customer_service import CustomerService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, not_found, error


def _serialize_customer(c) -> dict:
    return {
        "id": c.id,
        "uuid": str(c.uuid),
        "first_name": c.first_name,
        "last_name": c.last_name,
        "phone": c.phone,
        "telegram_id": c.telegram_id,
        "language": c.language,
        "is_active": c.is_active,
        "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
        "created_at": c.created_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def list_customers_view(request):
    svc = container.resolve(CustomerService)
    is_active_raw = request.GET.get("is_active")
    is_active = {"true": True, "false": False}.get(is_active_raw.lower()) if is_active_raw else None
    result = svc.get_all(
        query=request.GET.get("q"),
        is_active=is_active,
        order_by=request.GET.get("order_by", "-created_at"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
    )
    result["items"] = [_serialize_customer(c) for c in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_USERS)
def get_customer_view(request, customer_id):
    svc = container.resolve(CustomerService)
    customer = svc.get_by_id(customer_id)
    if not customer:
        return not_found("Customer not found")
    return success(data=_serialize_customer(customer))


@csrf_exempt
@require_http_methods(["PATCH"])
@require_permission(P.MANAGE_USERS)
def update_customer_view(request, customer_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    dto = UpdateCustomerDTO(**{k: v for k, v in data.items() if hasattr(UpdateCustomerDTO, k)})
    svc = container.resolve(CustomerService)
    result = svc.update_customer(customer_id, dto)
    return success(data=result, message="Customer updated")


@csrf_exempt
@require_http_methods(["POST"])
@require_permission(P.MANAGE_USERS)
def deactivate_customer_view(request, customer_id):
    svc = container.resolve(CustomerService)
    result = svc.deactivate(customer_id)
    return success(data=result)


@csrf_exempt
@require_http_methods(["POST"])
@require_permission(P.MANAGE_USERS)
def activate_customer_view(request, customer_id):
    svc = container.resolve(CustomerService)
    result = svc.activate(customer_id)
    return success(data=result)
