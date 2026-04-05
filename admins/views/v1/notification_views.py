import json
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from admins.dto.notification import CreateNotificationDTO, BulkNotificationDTO
from admins.services.v1.notification_service import NotificationService
from base.container import container
from base.permissions import require_permission, P
from base.responses import success, error, not_found


def _parse_bool(value):
    if not value:
        return None
    return {"true": True, "false": False}.get(value.lower())


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _serialize_notification(n) -> dict:
    data = {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "payload": n.payload,
        "channel": n.channel,
        "is_read": n.is_read,
        "sent_at": n.sent_at.isoformat(),
    }
    if hasattr(n, "user") and n.user:
        data["user"] = {
            "id": n.user.id,
            "first_name": n.user.first_name,
            "last_name": n.user.last_name,
            "phone": n.user.phone,
        }
    else:
        data["user_id"] = n.user_id
    return data


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_NOTIFICATIONS)
def list_notifications_view(request):
    svc = container.resolve(NotificationService)
    user_raw = request.GET.get("user_id")
    is_read = _parse_bool(request.GET.get("is_read"))
    result = svc.get_all(
        query=request.GET.get("q"),
        type=request.GET.get("type"),
        channel=request.GET.get("channel"),
        is_read=is_read,
        user_id=int(user_raw) if user_raw else None,
        order_by=request.GET.get("order_by", "-sent_at"),
        page=int(request.GET.get("page", 1)),
        per_page=int(request.GET.get("per_page", 20)),
    )
    result["items"] = [_serialize_notification(n) for n in result["items"]]
    return success(data=result)


@csrf_exempt
@require_GET
@require_permission(P.MANAGE_NOTIFICATIONS)
def get_notification_view(request, notification_id):
    svc = container.resolve(NotificationService)
    notif = svc.get_by_id(notification_id)
    if not notif:
        return not_found("Notification not found")
    return success(data=_serialize_notification(notif))


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_NOTIFICATIONS)
def send_notification_view(request, user_id):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["title", "body"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = CreateNotificationDTO(
        title=data["title"],
        body=data["body"],
        type=data.get("type", "promo"),
        channel=data.get("channel", "telegram"),
        payload=data.get("payload"),
    )
    svc = container.resolve(NotificationService)
    result = svc.send_to_user(user_id, dto)
    return success(data=result, message="Notification sent")


@csrf_exempt
@require_POST
@require_permission(P.MANAGE_NOTIFICATIONS)
def send_bulk_notification_view(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return error("Invalid JSON body")

    required = ["title", "body"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}", status=422)

    dto = BulkNotificationDTO(
        title=data["title"],
        body=data["body"],
        type=data.get("type", "promo"),
        channel=data.get("channel", "telegram"),
        payload=data.get("payload"),
        user_ids=data.get("user_ids"),
        role=data.get("role"),
    )
    svc = container.resolve(NotificationService)
    result = svc.send_bulk(dto)
    return success(data=result, message="Bulk notification sent")


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_NOTIFICATIONS)
def delete_notification_view(request, notification_id):
    svc = container.resolve(NotificationService)
    return success(data=svc.delete_notification(notification_id))


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission(P.MANAGE_NOTIFICATIONS)
def delete_user_notifications_view(request, user_id):
    svc = container.resolve(NotificationService)
    return success(data=svc.delete_user_notifications(user_id))


@csrf_exempt
@require_GET
@require_permission(P.VIEW_ANALYTICS)
def notification_stats_view(request):
    svc = container.resolve(NotificationService)
    date_from = _parse_date(request.GET.get("date_from"))
    date_to = _parse_date(request.GET.get("date_to"))
    return success(data=svc.stats(date_from=date_from, date_to=date_to))
