import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from base.container import container
from base.responses import success, error
from base.permissions import require_auth
from customer.services.v1.cart_service import CartService


@csrf_exempt
@require_GET
@require_auth
def get_cart_view(request):
    svc = container.resolve(CartService)
    return success(data=svc.get_cart(request.user_obj.id))


@csrf_exempt
@require_POST
@require_auth
def add_to_cart_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    if not product_id or quantity is None:
        return error("product_id and quantity are required", status=422)

    svc = container.resolve(CartService)
    result = svc.add_item(request.user_obj.id, int(product_id), str(quantity))
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def update_cart_item_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    if not product_id or quantity is None:
        return error("product_id and quantity are required", status=422)

    svc = container.resolve(CartService)
    result = svc.update_quantity(request.user_obj.id, int(product_id), str(quantity))
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def remove_cart_item_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    product_id = data.get("product_id")
    if not product_id:
        return error("product_id is required", status=422)

    svc = container.resolve(CartService)
    result = svc.remove_item(request.user_obj.id, int(product_id))
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def clear_cart_view(request):
    svc = container.resolve(CartService)
    result = svc.clear_cart(request.user_obj.id)
    return success(data=result)
