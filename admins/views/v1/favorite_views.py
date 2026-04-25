from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from admins.services.v1.favorite_service import FavoriteService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error


def _serialize_favorite(f) -> dict:
    data = {
        "id": f.id,
        "created_at": f.created_at.isoformat(),
    }
    if hasattr(f, "user") and f.user:
        data["user"] = {
            "id": f.user.id,
            "first_name": f.user.first_name,
            "last_name": f.user.last_name,
            "phone": f.user.phone,
        }
    else:
        data["user_id"] = f.user_id
    if hasattr(f, "product") and f.product:
        data["product"] = {
            "id": f.product.id,
            "name_uz": f.product.name_uz,
            "price": str(f.product.price),
        }
    else:
        data["product_id"] = f.product_id
    return data


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def list_favorites_view(request):
    svc = container.resolve(FavoriteService)
    user_raw = request.GET.get("user_id")
    product_raw = request.GET.get("product_id")
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        user_id=int(user_raw) if user_raw else None,
        product_id=int(product_raw) if product_raw else None,
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_favorite(f) for f in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def most_favorited_view(request):
    svc = container.resolve(FavoriteService)
    limit = int(request.GET.get("limit", 20))
    return success(data=svc.most_favorited(limit=limit))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def favorite_stats_view(request):
    svc = container.resolve(FavoriteService)
    return success(data=svc.stats())
