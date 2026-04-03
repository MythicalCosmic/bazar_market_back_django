from django.db.models import Count, Q

from base.interfaces.notification import INotificationRepository
from base.interfaces.user import IUserRepository
from base.exceptions import NotFoundError, ValidationError
from admins.dto.notification import CreateNotificationDTO, BulkNotificationDTO
from base.models import Notification, User


class NotificationService:
    def __init__(
        self,
        notification_repository: INotificationRepository,
        user_repository: IUserRepository,
    ):
        self.notif_repo = notification_repository
        self.user_repo = user_repository

    def get_all(
        self,
        query=None,
        type=None,
        channel=None,
        is_read=None,
        user_id=None,
        order_by="-sent_at",
        page=1,
        per_page=20,
    ):
        qs = self.notif_repo.get_all().select_related("user")

        if query:
            qs = self.notif_repo.search(qs, query, ["title", "body", "user__first_name", "user__phone"])
        if type:
            qs = qs.filter(type=type)
        if channel:
            qs = qs.filter(channel=channel)
        if is_read is not None:
            qs = qs.filter(is_read=is_read)
        if user_id is not None:
            qs = qs.filter(user_id=user_id)

        qs = self.notif_repo.apply_ordering(
            qs, order_by, {"sent_at", "type", "channel"}
        )
        return self.notif_repo.paginate(qs, page, per_page)

    def get_by_id(self, notif_id: int):
        return (
            self.notif_repo.get_all()
            .select_related("user")
            .filter(pk=notif_id)
            .first()
        )

    def send_to_user(self, user_id: int, dto: CreateNotificationDTO) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if dto.type not in dict(Notification.Type.choices):
            raise ValidationError(f"Invalid notification type: {dto.type}")
        if dto.channel not in dict(Notification.Channel.choices):
            raise ValidationError(f"Invalid channel: {dto.channel}")

        notif = self.notif_repo.create(
            user_id=user_id,
            title=dto.title,
            body=dto.body,
            type=dto.type,
            channel=dto.channel,
            payload=dto.payload,
        )
        return {"id": notif.id, "message": "Notification sent"}

    def send_bulk(self, dto: BulkNotificationDTO) -> dict:
        if dto.type not in dict(Notification.Type.choices):
            raise ValidationError(f"Invalid notification type: {dto.type}")
        if dto.channel not in dict(Notification.Channel.choices):
            raise ValidationError(f"Invalid channel: {dto.channel}")

        if dto.user_ids:
            users = self.user_repo.get_all().filter(pk__in=dto.user_ids, is_active=True)
        elif dto.role:
            if dto.role not in dict(User.Role.choices):
                raise ValidationError(f"Invalid role: {dto.role}")
            users = self.user_repo.get_all().filter(role=dto.role, is_active=True)
        else:
            users = self.user_repo.get_all().filter(is_active=True)

        notifications = [
            Notification(
                user_id=uid,
                title=dto.title,
                body=dto.body,
                type=dto.type,
                channel=dto.channel,
                payload=dto.payload,
            )
            for uid in users.values_list("id", flat=True)
        ]
        self.notif_repo.bulk_create(notifications)
        return {"sent": len(notifications), "message": "Notifications sent"}

    def delete_notification(self, notif_id: int) -> dict:
        notif = self.notif_repo.get_by_id(notif_id)
        if not notif:
            raise NotFoundError("Notification not found")
        self.notif_repo.delete(notif)
        return {"message": "Notification deleted"}

    def delete_user_notifications(self, user_id: int) -> dict:
        count = self.notif_repo.delete_by_user(user_id)
        return {"deleted": count}

    def stats(self, date_from=None, date_to=None) -> dict:
        qs = self.notif_repo.get_all()

        if date_from:
            qs = qs.filter(sent_at__gte=date_from)
        if date_to:
            qs = qs.filter(sent_at__lte=date_to)

        total = qs.count()
        by_type = dict(
            qs.values_list("type")
            .annotate(c=Count("id"))
            .values_list("type", "c")
        )
        by_channel = dict(
            qs.values_list("channel")
            .annotate(c=Count("id"))
            .values_list("channel", "c")
        )
        read = qs.filter(is_read=True).count()

        return {
            "total": total,
            "read": read,
            "unread": total - read,
            "read_rate": round(read / total * 100, 1) if total else 0,
            "by_type": by_type,
            "by_channel": by_channel,
        }
