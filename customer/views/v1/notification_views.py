from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from base.container import container
from base.responses import success
from base.permissions import require_auth
from customer.services.v1.notification_service import CustomerNotificationService


def _serialize_notification(n) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "payload": n.payload,
        "channel": n.channel,
        "is_read": n.is_read,
        "sent_at": n.sent_at.isoformat(),
    }


@csrf_exempt
@require_GET
@require_auth
def list_notifications_view(request):
    svc = container.resolve(CustomerNotificationService)
    result = svc.list_notifications(request.user_obj.id)
    result["items"] = [_serialize_notification(n) for n in result["items"]]
    return success(data=result)


@csrf_exempt
@require_POST
@require_auth
def mark_notification_read_view(request, notification_id):
    svc = container.resolve(CustomerNotificationService)
    return success(data=svc.mark_as_read(request.user_obj.id, notification_id))


@csrf_exempt
@require_POST
@require_auth
def mark_all_read_view(request):
    svc = container.resolve(CustomerNotificationService)
    return success(data=svc.mark_all_as_read(request.user_obj.id))


@csrf_exempt
@require_GET
@require_auth
def unread_count_view(request):
    svc = container.resolve(CustomerNotificationService)
    count = svc.unread_count(request.user_obj.id)
    return success(data={"unread_count": count})
