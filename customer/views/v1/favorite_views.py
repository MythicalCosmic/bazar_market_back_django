from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from base.container import container
from base.responses import success, error
from base.permissions import require_auth
from customer.services.v1.favorite_service import CustomerFavoriteService


def _serialize_favorite(f) -> dict:
    p = f.product
    return {
        "product_id": p.id,
        "name_uz": p.name_uz,
        "name_ru": p.name_ru,
        "price": str(p.price),
        "unit": p.unit,
        "in_stock": p.in_stock,
        "created_at": f.created_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_auth
def list_favorites_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CustomerFavoriteService)
    result = svc.list_favorites(request.user_obj.id, page=page, per_page=per_page)
    result["items"] = [_serialize_favorite(f) for f in result["items"]]
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def toggle_favorite_view(request, product_id):
    svc = container.resolve(CustomerFavoriteService)
    result = svc.toggle(request.user_obj.id, product_id)
    return success(data=result)


@csrf_exempt
@require_GET
@require_auth
def check_favorite_view(request, product_id):
    svc = container.resolve(CustomerFavoriteService)
    is_fav = svc.is_favorited(request.user_obj.id, product_id)
    return success(data={"product_id": product_id, "is_favorited": is_fav})
