import json
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.services.v1.review_service import ReviewService
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


def _serialize_review(r) -> dict:
    data = {
        "id": r.id,
        "rating": r.rating,
        "comment": r.comment,
        "admin_reply": r.admin_reply,
        "moderation_status": r.moderation_status,
        "created_at": r.created_at.isoformat(),
    }
    if hasattr(r, "user") and r.user:
        data["user"] = {
            "id": r.user.id,
            "first_name": r.user.first_name,
            "last_name": r.user.last_name,
            "phone": r.user.phone,
        }
    else:
        data["user_id"] = r.user_id
    if hasattr(r, "order") and r.order:
        data["order"] = {
            "id": r.order.id,
            "order_number": r.order.order_number,
        }
    else:
        data["order_id"] = r.order_id
    if hasattr(r, "moderated_by") and r.moderated_by:
        data["moderated_by"] = r.moderated_by.first_name
        data["moderated_at"] = r.moderated_at.isoformat() if r.moderated_at else None
    return data


@csrf_exempt
@require_GET
@require_permission(P.VIEW_REVIEWS)
def list_reviews_view(request):
    svc = container.resolve(ReviewService)
    user_raw = request.GET.get("user_id")
    rating_raw = request.GET.get("rating")
    try:
        page = int(request.GET.get("page", 1))
        per_page = int(request.GET.get("per_page", 20))
    except (ValueError, TypeError):
        return error("page and per_page must be integers", status=422)

    result = svc.get_all(
        query=request.GET.get("q"),
        rating=int(rating_raw) if rating_raw else None,
        moderation_status=request.GET.get("moderation_status"),
        user_id=int(user_raw) if user_raw else None,
        order_by=request.GET.get("order_by", "-created_at"),
        page=page,
        per_page=per_page,
    )
    result["items"] = [_serialize_review(r) for r in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_REVIEWS)
def get_review_view(request, review_id):
    svc = container.resolve(ReviewService)
    review = svc.get_by_id(review_id)
    if not review:
        return not_found("Review not found")
    return success(data=_serialize_review(review))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REVIEWS)
def approve_review_view(request, review_id):
    svc = container.resolve(ReviewService)
    result = svc.approve(review_id, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REVIEWS)
def reject_review_view(request, review_id):
    svc = container.resolve(ReviewService)
    result = svc.reject(review_id, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REVIEWS)
def reply_review_view(request, review_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    reply_text = data.get("reply", "").strip()
    if not reply_text:
        return error("reply is required", status=422)

    svc = container.resolve(ReviewService)
    result = svc.reply(review_id, reply_text, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_REVIEWS)
def delete_review_view(request, review_id):
    svc = container.resolve(ReviewService)
    return success(data=svc.delete_review(review_id))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REVIEWS)
def bulk_approve_reviews_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    review_ids = data.get("review_ids")
    if not isinstance(review_ids, list) or not all(isinstance(i, int) for i in review_ids):
        return error("review_ids must be a list of integers", status=422)

    svc = container.resolve(ReviewService)
    result = svc.bulk_approve(review_ids, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_REVIEWS)
def bulk_reject_reviews_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    review_ids = data.get("review_ids")
    if not isinstance(review_ids, list) or not all(isinstance(i, int) for i in review_ids):
        return error("review_ids must be a list of integers", status=422)

    svc = container.resolve(ReviewService)
    result = svc.bulk_reject(review_ids, admin_user=request.user_obj)
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def review_stats_view(request):
    svc = container.resolve(ReviewService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.stats(date_from=date_from, date_to=date_to))
