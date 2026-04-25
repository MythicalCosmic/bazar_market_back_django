import json

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from base.container import container
from base.responses import success, error, created
from base.permissions import require_auth
from customer.dto.review import CreateReviewDTO
from customer.services.v1.review_service import CustomerReviewService


def _serialize_review(r) -> dict:
    data = {
        "id": r.id,
        "order_id": r.order_id,
        "rating": r.rating,
        "comment": r.comment,
        "admin_reply": r.admin_reply,
        "moderation_status": r.moderation_status,
        "created_at": r.created_at.isoformat(),
    }
    if hasattr(r, "order") and r.order:
        data["order_number"] = r.order.order_number
    return data


@csrf_exempt
@require_POST
@require_auth
def submit_review_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    order_id = data.get("order_id")
    rating = data.get("rating")
    if not order_id or rating is None:
        return error("order_id and rating are required", status=422)

    dto = CreateReviewDTO(
        order_id=int(order_id),
        rating=int(rating),
        comment=data.get("comment", ""),
    )
    svc = container.resolve(CustomerReviewService)
    result = svc.submit_review(request.user_obj.id, dto)
    return created(data=result, message="Review submitted")


@csrf_exempt
@require_GET
@require_auth
def list_my_reviews_view(request):
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    svc = container.resolve(CustomerReviewService)
    result = svc.list_my_reviews(request.user_obj.id, page=page, per_page=per_page)
    result["items"] = [_serialize_review(r) for r in result["items"]]
    return success(data=result)
